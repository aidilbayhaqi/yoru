import uuid
from datetime import UTC, datetime
from pathlib import PurePath

from yoru_api.core.problem import AppError
from yoru_api.modules.identity.models import Partner
from yoru_api.modules.identity.permissions import Actor, require_permission
from yoru_api.modules.partners.models import (
    PartnerDocument,
    PartnerVerification,
    ServiceArea,
)
from yoru_api.modules.partners.repository import PartnerBundle, PartnerRepository
from yoru_api.modules.partners.schemas import (
    CreatePartnerRequest,
    CreateServiceAreaRequest,
    RegisterDocumentRequest,
    ReviewDecisionRequest,
    ScanResultRequest,
    UpdatePartnerRequest,
)
from yoru_api.modules.partners.state_machine import ensure_partner_transition

REQUIRED_DOCUMENT_KINDS = frozenset({"business_registration", "owner_identity"})
EDITABLE_PARTNER_STATES = frozenset({"draft", "revision_required"})


class PartnerService:
    def __init__(self, repository: PartnerRepository) -> None:
        self._repository = repository

    async def create_partner(
        self,
        *,
        actor: Actor,
        payload: CreatePartnerRequest,
    ) -> PartnerBundle:
        try:
            partner = await self._repository.create_partner(
                owner_user_id=actor.user_id,
                values=payload.model_dump(),
            )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner.id,
                action="partner.application.created",
                resource_type="partner",
                resource_id=str(partner.id),
            )
            await self._repository.flush()
            bundle = await self._repository.get_bundle(partner.id)
            if bundle is None:
                raise RuntimeError("created partner cannot be loaded")
            await self._repository.commit()
            return bundle
        except Exception:
            await self._repository.rollback()
            raise

    async def get_partner(self, *, actor: Actor, partner_id: uuid.UUID) -> PartnerBundle:
        require_permission(actor, "partner.profile.read", partner_id=partner_id)
        return await self._required_bundle(partner_id)

    async def update_partner(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID,
        payload: UpdatePartnerRequest,
    ) -> PartnerBundle:
        require_permission(actor, "partner.profile.write", partner_id=partner_id)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            if partner.status not in EDITABLE_PARTNER_STATES:
                raise AppError(
                    409,
                    "PARTNER_PROFILE_LOCKED",
                    "Partner profile is locked",
                    "Profile can only be edited while draft or revision is required.",
                )
            changes = payload.model_dump(exclude_unset=True)
            if not changes:
                raise AppError(400, "PARTNER_UPDATE_EMPTY", "No profile changes supplied")
            for field, value in changes.items():
                setattr(partner, field, value)
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.profile.updated",
                resource_type="partner",
                resource_id=str(partner_id),
                metadata={"fields": ",".join(sorted(changes))},
            )
            await self._repository.flush()
            bundle = await self._required_bundle(partner_id)
            await self._repository.commit()
            return bundle
        except Exception:
            await self._repository.rollback()
            raise

    async def add_service_area(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID,
        payload: CreateServiceAreaRequest,
    ) -> ServiceArea:
        require_permission(actor, "partner.service_area.write", partner_id=partner_id)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            self._ensure_editable(partner.status)
            service_area = self._repository.add_service_area(
                partner_id=partner_id,
                values=payload.model_dump(),
            )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.service_area.created",
                resource_type="service_area",
                resource_id=str(service_area.id),
            )
            await self._repository.commit()
            return service_area
        except Exception:
            await self._repository.rollback()
            raise

    async def delete_service_area(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID,
        service_area_id: uuid.UUID,
    ) -> None:
        require_permission(actor, "partner.service_area.write", partner_id=partner_id)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            self._ensure_editable(partner.status)
            deleted = await self._repository.delete_service_area(
                partner_id=partner_id,
                service_area_id=service_area_id,
            )
            if not deleted:
                raise AppError(404, "SERVICE_AREA_NOT_FOUND", "Service area not found")
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.service_area.deleted",
                resource_type="service_area",
                resource_id=str(service_area_id),
            )
            await self._repository.commit()
        except Exception:
            await self._repository.rollback()
            raise

    async def register_document(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID,
        payload: RegisterDocumentRequest,
    ) -> PartnerDocument:
        require_permission(actor, "partner.document.write", partner_id=partner_id)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            self._ensure_editable(partner.status)
            safe_filename = PurePath(payload.original_filename).name
            contains_separator = (
                "/" in payload.original_filename
                or "\\" in payload.original_filename
            )
            if (
                contains_separator
                or safe_filename != payload.original_filename
                or safe_filename in {"", ".", ".."}
            ):
                raise AppError(
                    422,
                    "DOCUMENT_FILENAME_INVALID",
                    "Document filename is invalid",
                )
            document_id = uuid.uuid4()
            values = payload.model_dump()
            values["original_filename"] = safe_filename
            document = self._repository.add_document(
                document_id=document_id,
                partner_id=partner_id,
                uploaded_by_user_id=actor.user_id,
                values=values,
            )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.document.registered",
                resource_type="partner_document",
                resource_id=str(document.id),
                metadata={"kind": document.kind},
            )
            await self._repository.commit()
            return document
        except Exception:
            await self._repository.rollback()
            raise

    async def mark_scan_result(
        self,
        *,
        actor: Actor,
        document_id: uuid.UUID,
        payload: ScanResultRequest,
    ) -> PartnerDocument:
        require_permission(
            actor,
            "platform.partner.document.scan",
            require_mfa=True,
        )
        try:
            document = await self._repository.get_document(document_id, for_update=True)
            if document is None:
                raise AppError(404, "PARTNER_DOCUMENT_NOT_FOUND", "Partner document not found")
            document.scan_status = payload.status.value
            document.scan_detail = payload.detail
            document.scanned_at = datetime.now(UTC)
            document.verification_status = (
                "pending" if payload.status.value == "clean" else "rejected"
            )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=document.partner_id,
                action="partner.document.scan_completed",
                resource_type="partner_document",
                resource_id=str(document.id),
                metadata={"scan_status": document.scan_status},
            )
            await self._repository.commit()
            return document
        except Exception:
            await self._repository.rollback()
            raise

    async def submit(self, *, actor: Actor, partner_id: uuid.UUID) -> PartnerBundle:
        require_permission(actor, "partner.profile.write", partner_id=partner_id)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            ensure_partner_transition(partner.status, "submitted")
            bundle = await self._required_bundle(partner_id)
            self._validate_submission(bundle)
            now = datetime.now(UTC)
            partner.status = "submitted"
            partner.submitted_at = now
            partner.review_reason = None
            bundle.verification.status = "submitted"
            bundle.verification.reason = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.application.submitted",
                resource_type="partner",
                resource_id=str(partner_id),
            )
            self._repository.add_outbox(
                aggregate_type="partner",
                aggregate_id=str(partner_id),
                event_type="partner.application.submitted",
                payload={"partner_id": str(partner_id), "submitted_at": now.isoformat()},
            )
            await self._repository.flush()
            result = await self._required_bundle(partner_id)
            await self._repository.commit()
            return result
        except Exception:
            await self._repository.rollback()
            raise

    async def list_for_review(
        self,
        *,
        actor: Actor,
        status: str | None,
        limit: int,
    ) -> list[PartnerBundle]:
        require_permission(actor, "platform.partner.verify", require_mfa=True)
        return await self._repository.list_bundles(status=status, limit=limit)

    async def start_review(self, *, actor: Actor, partner_id: uuid.UUID) -> PartnerBundle:
        require_permission(actor, "platform.partner.verify", require_mfa=True)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            verification = await self._required_verification(partner_id, for_update=True)
            ensure_partner_transition(partner.status, "under_review")
            now = datetime.now(UTC)
            partner.status = "under_review"
            verification.status = "under_review"
            verification.reviewer_id = actor.user_id
            verification.started_at = now
            verification.reason = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.review.started",
                resource_type="partner_verification",
                resource_id=str(verification.id),
            )
            await self._repository.flush()
            result = await self._required_bundle(partner_id)
            await self._repository.commit()
            return result
        except Exception:
            await self._repository.rollback()
            raise

    async def decide_review(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID,
        payload: ReviewDecisionRequest,
    ) -> PartnerBundle:
        require_permission(actor, "platform.partner.verify", require_mfa=True)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            verification = await self._required_verification(partner_id, for_update=True)
            target = payload.decision.value
            ensure_partner_transition(partner.status, target)
            checklist_incomplete = not payload.checklist or not all(payload.checklist.values())
            if target == "verified" and checklist_incomplete:
                raise AppError(
                    409,
                    "VERIFICATION_CHECKLIST_INCOMPLETE",
                    "Verification checklist is incomplete",
                )
            now = datetime.now(UTC)
            partner.status = target
            partner.reviewed_at = now
            partner.reviewed_by_user_id = actor.user_id
            partner.review_reason = payload.reason
            verification.status = target
            verification.reviewer_id = actor.user_id
            verification.reason = payload.reason
            verification.checklist = payload.checklist
            verification.decided_at = now
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action=f"partner.review.{target}",
                resource_type="partner_verification",
                resource_id=str(verification.id),
                metadata={"decision": target},
            )
            self._repository.add_outbox(
                aggregate_type="partner",
                aggregate_id=str(partner_id),
                event_type=f"partner.verification.{target}",
                payload={"partner_id": str(partner_id), "decision": target},
            )
            await self._repository.flush()
            result = await self._required_bundle(partner_id)
            await self._repository.commit()
            return result
        except Exception:
            await self._repository.rollback()
            raise

    async def block(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID,
        reason: str,
    ) -> PartnerBundle:
        require_permission(actor, "platform.partner.block", require_mfa=True)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            ensure_partner_transition(partner.status, "suspended")
            verification = await self._required_verification(partner_id, for_update=True)
            now = datetime.now(UTC)
            partner.status = "suspended"
            partner.reviewed_at = now
            partner.reviewed_by_user_id = actor.user_id
            partner.review_reason = reason
            verification.status = "suspended"
            verification.reviewer_id = actor.user_id
            verification.reason = reason
            verification.decided_at = now
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.blocked",
                resource_type="partner",
                resource_id=str(partner_id),
                metadata={"reason": reason},
            )
            self._repository.add_outbox(
                aggregate_type="partner",
                aggregate_id=str(partner_id),
                event_type="partner.suspended",
                payload={"partner_id": str(partner_id), "reason": reason},
            )
            await self._repository.flush()
            result = await self._required_bundle(partner_id)
            await self._repository.commit()
            return result
        except Exception:
            await self._repository.rollback()
            raise

    async def reinstate(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID,
        reason: str,
    ) -> PartnerBundle:
        require_permission(actor, "platform.partner.block", require_mfa=True)
        try:
            partner = await self._required_partner(partner_id, for_update=True)
            ensure_partner_transition(partner.status, "verified")
            verification = await self._required_verification(partner_id, for_update=True)
            now = datetime.now(UTC)
            partner.status = "verified"
            partner.reviewed_at = now
            partner.reviewed_by_user_id = actor.user_id
            partner.review_reason = reason
            verification.status = "verified"
            verification.reviewer_id = actor.user_id
            verification.reason = reason
            verification.decided_at = now
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="partner.reinstated",
                resource_type="partner",
                resource_id=str(partner_id),
                metadata={"reason": reason},
            )
            await self._repository.flush()
            result = await self._required_bundle(partner_id)
            await self._repository.commit()
            return result
        except Exception:
            await self._repository.rollback()
            raise

    async def _required_partner(
        self,
        partner_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Partner:
        partner = await self._repository.get_partner(partner_id, for_update=for_update)
        if partner is None:
            raise AppError(404, "PARTNER_NOT_FOUND", "Partner not found")
        return partner

    async def _required_verification(
        self,
        partner_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> PartnerVerification:
        verification = await self._repository.get_verification(
            partner_id,
            for_update=for_update,
        )
        if verification is None:
            raise AppError(500, "PARTNER_VERIFICATION_MISSING", "Verification record is missing")
        return verification

    async def _required_bundle(self, partner_id: uuid.UUID) -> PartnerBundle:
        bundle = await self._repository.get_bundle(partner_id)
        if bundle is None:
            raise AppError(404, "PARTNER_NOT_FOUND", "Partner not found")
        return bundle

    @staticmethod
    def _ensure_editable(status: str) -> None:
        if status not in EDITABLE_PARTNER_STATES:
            raise AppError(
                409,
                "PARTNER_PROFILE_LOCKED",
                "Partner profile is locked",
                "Profile can only be edited while draft or revision is required.",
            )

    @staticmethod
    def _validate_submission(bundle: PartnerBundle) -> None:
        partner = bundle.partner
        required_profile = {
            "legal_name": partner.legal_name,
            "partner_type": partner.partner_type,
            "contact_email": partner.contact_email,
            "contact_phone": partner.contact_phone,
            "address_line": partner.address_line,
            "city": partner.city,
            "province": partner.province,
        }
        missing_fields = sorted(name for name, value in required_profile.items() if not value)
        if missing_fields:
            raise AppError(
                409,
                "PARTNER_PROFILE_INCOMPLETE",
                "Partner profile is incomplete",
                f"Missing fields: {', '.join(missing_fields)}.",
            )
        if not bundle.service_areas:
            raise AppError(
                409,
                "SERVICE_AREA_REQUIRED",
                "At least one service area is required",
            )
        now = datetime.now(UTC)
        clean_kinds = {
            document.kind
            for document in bundle.documents
            if document.scan_status == "clean"
            and (document.expires_at is None or document.expires_at > now)
        }
        missing_documents = sorted(REQUIRED_DOCUMENT_KINDS - clean_kinds)
        if missing_documents:
            raise AppError(
                409,
                "PARTNER_DOCUMENTS_INCOMPLETE",
                "Required partner documents are missing or not clean",
                f"Required clean documents: {', '.join(missing_documents)}.",
            )
