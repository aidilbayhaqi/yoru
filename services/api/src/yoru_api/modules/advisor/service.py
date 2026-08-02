import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.advisor import CONSENT_VERSION, ENGINE_VERSION
from yoru_api.modules.advisor.domain import (
    Candidate,
    assess_safety,
    build_explanation,
    evaluate_cases,
    rank_candidates,
    request_fingerprint,
)
from yoru_api.modules.advisor.models import AiAdvisorSession
from yoru_api.modules.advisor.repository import AdvisorRepository
from yoru_api.modules.advisor.schemas import (
    AdvisorSessionCreate,
    EvaluationCreate,
    FeedbackCreate,
    MediaRegister,
    MediaScanResult,
)
from yoru_api.modules.commerce.domain import to_minor_units
from yoru_api.modules.identity.permissions import Actor, require_permission

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class AdvisorService:
    def __init__(self, repository: AdvisorRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)

    def _require_enabled(self) -> None:
        if not self._settings.feature_customer_ai:
            raise AppError(404, "FEATURE_DISABLED", "Customer AI Advisor is disabled")

    async def current_consent(self, actor: Actor):
        self._require_enabled()
        item = await self._repository.active_consent(actor.user_id)
        if item is None:
            raise AppError(404, "AI_CONSENT_NOT_FOUND", "Active AI consent was not found")
        return item

    async def grant_consent(
        self,
        actor: Actor,
        *,
        photo_processing: bool,
        personalization: bool,
        retention_days: int,
    ):
        self._require_enabled()
        now = self.now()
        await self._repository.revoke_active_consents(actor.user_id, now)
        item = await self._repository.add_consent(
            customer_id=actor.user_id,
            scope="customer_ai",
            version=CONSENT_VERSION,
            status="active",
            photo_processing=photo_processing,
            personalization=personalization,
            retention_days=retention_days,
            granted_at=now,
            revoked_at=None,
        )
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.consent.granted",
            resource_type="ai_consent",
            resource_id=str(item.id),
            metadata={
                "photo_processing": photo_processing,
                "personalization": personalization,
                "retention_days": retention_days,
                "version": CONSENT_VERSION,
            },
        )
        await self._repository.commit()
        await self._repository.refresh(item)
        return item

    async def revoke_consent(self, actor: Actor) -> None:
        self._require_enabled()
        count = await self._repository.revoke_active_consents(actor.user_id, self.now())
        if count == 0:
            raise AppError(404, "AI_CONSENT_NOT_FOUND", "Active AI consent was not found")
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.consent.revoked",
            resource_type="user",
            resource_id=str(actor.user_id),
        )
        await self._repository.commit()

    async def create_session(self, actor: Actor, payload: AdvisorSessionCreate):
        self._require_enabled()
        consent = await self._repository.active_consent(actor.user_id)
        if consent is None:
            raise AppError(412, "AI_CONSENT_REQUIRED", "Active AI consent is required")
        now = self.now()
        combined_text = " ".join((payload.goal, *payload.concerns))
        safety = assess_safety(combined_text)
        status = "blocked" if safety.status == "blocked" else "collecting"
        summary = safety.guidance if safety.status == "blocked" else None
        item = await self._repository.add_session(
            customer_id=actor.user_id,
            consent_id=consent.id,
            status=status,
            goal=payload.goal.strip(),
            concerns=payload.concerns,
            preferences=payload.preferences,
            safety_status=safety.status,
            safety_reason=safety.reason,
            request_hash=request_fingerprint(
                goal=payload.goal,
                concerns=payload.concerns,
                preferences=payload.preferences,
            ),
            model_provider="local",
            model_version=ENGINE_VERSION,
            summary=summary,
            expires_at=now + timedelta(days=consent.retention_days),
            completed_at=now if status == "blocked" else None,
        )
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.session.created",
            resource_type="ai_advisor_session",
            resource_id=str(item.id),
            metadata={"safety_status": safety.status, "model_version": ENGINE_VERSION},
        )
        self._repository.outbox(
            aggregate_type="ai_advisor_session",
            aggregate_id=str(item.id),
            event_type="ai.advisor.session.created",
            payload={"session_id": str(item.id), "customer_id": str(actor.user_id)},
        )
        await self._repository.commit()
        await self._repository.refresh(item)
        return item

    async def _owned_session(
        self, actor: Actor, session_id: uuid.UUID, *, for_update: bool = False
    ) -> AiAdvisorSession:
        item = await self._repository.get_session(session_id, for_update=for_update)
        if item is None or item.customer_id != actor.user_id:
            raise AppError(404, "AI_SESSION_NOT_FOUND", "AI Advisor session was not found")
        return item

    async def session_detail(self, actor: Actor, session_id: uuid.UUID):
        self._require_enabled()
        item = await self._owned_session(actor, session_id)
        media = await self._repository.list_media(item.id)
        recommendations = await self._repository.list_recommendations(item.id)
        return item, media, recommendations

    async def list_sessions(self, actor: Actor, limit: int):
        self._require_enabled()
        return await self._repository.list_sessions(actor.user_id, limit=limit)

    async def register_media(
        self, actor: Actor, session_id: uuid.UUID, payload: MediaRegister
    ):
        self._require_enabled()
        item = await self._owned_session(actor, session_id)
        if item.status in {"blocked", "expired"}:
            raise AppError(409, "AI_SESSION_NOT_WRITABLE", "Session cannot accept media")
        consent = await self._repository.active_consent(actor.user_id)
        if consent is None or consent.id != item.consent_id:
            raise AppError(412, "AI_CONSENT_REQUIRED", "Active AI consent is required")
        if not consent.photo_processing:
            raise AppError(
                412,
                "AI_PHOTO_CONSENT_REQUIRED",
                "Photo-processing consent is required",
            )
        safe_name = _SAFE_FILENAME.sub("-", payload.original_filename).strip(".-") or "image"
        media_id = uuid.uuid4()
        object_key = (
            f"quarantine/customer-ai/{actor.user_id}/{item.id}/{media_id}-{safe_name[:120]}"
        )
        asset = await self._repository.add_media(
            id=media_id,
            session_id=item.id,
            customer_id=actor.user_id,
            object_key=object_key,
            original_filename=payload.original_filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            sha256=payload.sha256.lower(),
            status="pending_scan",
            scan_result={},
            retention_expires_at=item.expires_at,
            scanned_at=None,
            deleted_at=None,
        )
        self._repository.outbox(
            aggregate_type="ai_media_asset",
            aggregate_id=str(asset.id),
            event_type="ai.media.scan.requested",
            payload={
                "media_id": str(asset.id),
                "object_key": object_key,
                "content_type": asset.content_type,
                "sha256": asset.sha256,
            },
        )
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.media.registered",
            resource_type="ai_media_asset",
            resource_id=str(asset.id),
            metadata={"session_id": str(item.id), "status": asset.status},
        )
        await self._repository.commit()
        await self._repository.refresh(asset)
        return asset

    async def record_scan(self, actor: Actor, media_id: uuid.UUID, payload: MediaScanResult):
        self._require_enabled()
        require_permission(actor, "platform.ai.manage", require_mfa=True)
        asset = await self._repository.get_media(media_id, for_update=True)
        if asset is None:
            raise AppError(404, "AI_MEDIA_NOT_FOUND", "AI media asset was not found")
        if asset.status == "deleted":
            raise AppError(409, "AI_MEDIA_DELETED", "AI media asset was deleted")
        asset.status = payload.result
        asset.scan_result = {"scanner": payload.scanner, "detail": payload.detail}
        asset.scanned_at = self.now()
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.media.scanned",
            resource_type="ai_media_asset",
            resource_id=str(asset.id),
            metadata={"result": payload.result, "scanner": payload.scanner},
        )
        self._repository.outbox(
            aggregate_type="ai_media_asset",
            aggregate_id=str(asset.id),
            event_type=f"ai.media.scan.{payload.result}",
            payload={"media_id": str(asset.id), "result": payload.result},
        )
        await self._repository.commit()
        await self._repository.refresh(asset)
        return asset

    async def analyze(self, actor: Actor, session_id: uuid.UUID):
        self._require_enabled()
        item = await self._owned_session(actor, session_id, for_update=True)
        if item.status == "expired":
            raise AppError(410, "AI_SESSION_EXPIRED", "AI Advisor session has expired")
        if item.status == "blocked":
            return item, []

        consent = await self._repository.active_consent(actor.user_id)
        if consent is None or consent.id != item.consent_id:
            raise AppError(412, "AI_CONSENT_REQUIRED", "Active AI consent is required")
        media = await self._repository.list_media(item.id)
        unsafe_media = [asset for asset in media if asset.status != "clean"]
        if unsafe_media:
            raise AppError(
                409,
                "AI_MEDIA_NOT_READY",
                "All registered media must pass malware scanning before analysis",
            )

        combined = " ".join(
            (
                item.goal,
                *item.concerns,
                *(f"{key} {value}" for key, value in item.preferences.items()),
            )
        )
        safety = assess_safety(combined)
        item.safety_status = safety.status
        item.safety_reason = safety.reason
        if safety.status == "blocked":
            item.status = "blocked"
            item.summary = safety.guidance
            item.completed_at = self.now()
            await self._repository.replace_recommendations(item.id, [])
            await self._repository.commit()
            return item, []

        products = await self._repository.published_products()
        services = await self._repository.published_services()
        candidates: list[Candidate] = []
        for product in products:
            candidates.append(
                Candidate(
                    item_type="product",
                    item_id=product.id,
                    partner_id=product.partner_id,
                    title=product.name,
                    description=product.description,
                    price_minor=to_minor_units(product.unit_price),
                    currency=product.currency,
                )
            )
        for service in services:
            candidates.append(
                Candidate(
                    item_type="service",
                    item_id=service.id,
                    partner_id=service.partner_id,
                    title=service.name,
                    description=service.description,
                    price_minor=to_minor_units(service.price),
                    currency=service.currency,
                )
            )

        ranked = rank_candidates(combined, candidates, limit=5)
        values: list[dict[str, object]] = []
        for index, ranked_item in enumerate(ranked, start=1):
            candidate = ranked_item.candidate
            values.append(
                {
                    "session_id": item.id,
                    "customer_id": actor.user_id,
                    "partner_id": candidate.partner_id,
                    "product_id": candidate.item_id if candidate.item_type == "product" else None,
                    "service_id": candidate.item_id if candidate.item_type == "service" else None,
                    "item_type": candidate.item_type,
                    "rank": index,
                    "score": Decimal(str(ranked_item.score)),
                    "title": candidate.title,
                    "explanation": build_explanation(ranked_item),
                    "evidence": {
                        "matched_terms": list(ranked_item.matched_terms),
                        "source": "published_catalog",
                        "item_id": str(candidate.item_id),
                    },
                    "price_snapshot": candidate.price_minor,
                    "currency": candidate.currency,
                }
            )
        recommendations = await self._repository.replace_recommendations(item.id, values)
        item.status = "completed"
        item.summary = (
            f"Ditemukan {len(recommendations)} rekomendasi berbasis katalog terpublikasi."
            if recommendations
            else "Belum ada item katalog terpublikasi yang cukup cocok dengan kebutuhan ini."
        )
        if safety.guidance:
            item.summary = f"{item.summary} {safety.guidance}"
        item.completed_at = self.now()
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.session.analyzed",
            resource_type="ai_advisor_session",
            resource_id=str(item.id),
            metadata={
                "recommendation_count": len(recommendations),
                "safety_status": safety.status,
                "engine_version": ENGINE_VERSION,
            },
        )
        self._repository.outbox(
            aggregate_type="ai_advisor_session",
            aggregate_id=str(item.id),
            event_type="ai.advisor.completed",
            payload={
                "session_id": str(item.id),
                "recommendation_count": len(recommendations),
            },
        )
        await self._repository.commit()
        await self._repository.refresh(item)
        return item, recommendations

    async def feedback(self, actor: Actor, session_id: uuid.UUID, payload: FeedbackCreate):
        self._require_enabled()
        item = await self._owned_session(actor, session_id)
        if item.status not in {"completed", "blocked"}:
            raise AppError(409, "AI_SESSION_NOT_COMPLETE", "Session is not complete")
        try:
            feedback = await self._repository.add_feedback(
                session_id=item.id,
                customer_id=actor.user_id,
                rating=payload.rating,
                helpful=payload.helpful,
                reason_codes=payload.reason_codes,
                comment=payload.comment,
            )
        except IntegrityError as error:
            raise AppError(409, "AI_FEEDBACK_EXISTS", "Feedback already exists") from error
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.feedback.created",
            resource_type="ai_feedback",
            resource_id=str(feedback.id),
            metadata={"session_id": str(item.id), "rating": payload.rating},
        )
        await self._repository.commit()
        await self._repository.refresh(feedback)
        return feedback

    async def run_evaluation(self, actor: Actor, payload: EvaluationCreate):
        self._require_enabled()
        require_permission(actor, "platform.ai.evaluate", require_mfa=True)
        now = self.now()
        cases = [case.model_dump() for case in payload.cases]
        metrics = evaluate_cases(cases)
        item = await self._repository.add_evaluation(
            dataset_name=payload.dataset_name,
            engine_version=ENGINE_VERSION,
            status="completed",
            metrics=metrics,
            cases=cases,
            created_by_user_id=actor.user_id,
            started_at=now,
            completed_at=self.now(),
        )
        self._repository.audit(
            actor_id=actor.user_id,
            action="ai.evaluation.completed",
            resource_type="ai_evaluation_run",
            resource_id=str(item.id),
            metadata={"dataset_name": payload.dataset_name, **metrics},
        )
        await self._repository.commit()
        await self._repository.refresh(item)
        return item

    async def list_evaluations(self, actor: Actor, limit: int):
        self._require_enabled()
        require_permission(actor, "platform.ai.read")
        return await self._repository.list_evaluations(limit=limit)

    async def purge_expired(self, actor: Actor, limit: int) -> tuple[int, int]:
        self._require_enabled()
        require_permission(actor, "platform.ai.manage", require_mfa=True)
        now = self.now()
        sessions = await self._repository.expired_sessions(now, limit=limit)
        media_deleted = 0
        for item in sessions:
            media_deleted += await self._repository.minimize_expired_session(item, now)
        if sessions:
            self._repository.audit(
                actor_id=actor.user_id,
                action="ai.retention.purged",
                resource_type="ai_advisor_session",
                resource_id="batch",
                metadata={
                    "sessions_expired": len(sessions),
                    "media_deleted": media_deleted,
                },
            )
        await self._repository.commit()
        return len(sessions), media_deleted
