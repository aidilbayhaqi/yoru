import uuid
from dataclasses import dataclass
from sqlalchemy import Select, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent, OutboxEvent
from yoru_api.modules.identity.models import Partner, PartnerMembership, Role
from yoru_api.modules.partners.models import (
    PartnerDocument,
    PartnerVerification,
    ServiceArea,
)


@dataclass(frozen=True, slots=True)
class PartnerBundle:
    partner: Partner
    verification: PartnerVerification
    documents: list[PartnerDocument]
    service_areas: list[ServiceArea]


class PartnerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_partner(
        self,
        *,
        owner_user_id: uuid.UUID,
        values: dict[str, object],
    ) -> Partner:
        owner_role_id = await self._session.scalar(
            select(Role.id).where(Role.code == "partner_owner", Role.scope == "partner")
        )
        if owner_role_id is None:
            raise RuntimeError("partner_owner role seed is missing")

        partner_id = uuid.uuid4()
        await self._session.execute(
            text("SELECT set_config('app.partner_application_id', :partner_id, true)"),
            {"partner_id": str(partner_id)},
        )
        partner = Partner(
            id=partner_id,
            **values,
            status="draft",
            created_by_user_id=owner_user_id,
        )
        self._session.add(partner)
        await self._session.flush()
        self._session.add(
            PartnerMembership(
                partner_id=partner.id,
                user_id=owner_user_id,
                role_id=owner_role_id,
                status="active",
            )
        )
        self._session.add(
            PartnerVerification(
                partner_id=partner.id,
                status="draft",
                checklist={},
            )
        )
        await self._session.flush()
        return partner

    async def get_partner(
        self,
        partner_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Partner | None:
        statement: Select[tuple[Partner]] = select(Partner).where(Partner.id == partner_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_verification(
        self,
        partner_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> PartnerVerification | None:
        statement: Select[tuple[PartnerVerification]] = select(PartnerVerification).where(
            PartnerVerification.partner_id == partner_id
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_document(
        self,
        document_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> PartnerDocument | None:
        statement: Select[tuple[PartnerDocument]] = select(PartnerDocument).where(
            PartnerDocument.id == document_id
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_bundle(self, partner_id: uuid.UUID) -> PartnerBundle | None:
        partner = await self.get_partner(partner_id)
        if partner is None:
            return None
        verification = await self.get_verification(partner_id)
        if verification is None:
            raise RuntimeError("partner verification row is missing")
        documents = list(
            await self._session.scalars(
                select(PartnerDocument)
                .where(PartnerDocument.partner_id == partner_id)
                .order_by(PartnerDocument.created_at.desc(), PartnerDocument.id.desc())
            )
        )
        service_areas = list(
            await self._session.scalars(
                select(ServiceArea)
                .where(ServiceArea.partner_id == partner_id)
                .order_by(ServiceArea.created_at.asc(), ServiceArea.id.asc())
            )
        )
        return PartnerBundle(partner, verification, documents, service_areas)

    async def list_bundles(
        self,
        *,
        status: str | None,
        limit: int,
    ) -> list[PartnerBundle]:
        statement = (
            select(Partner)
            .order_by(Partner.updated_at.desc(), Partner.id.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(Partner.status == status)
        partners = list(await self._session.scalars(statement))
        bundles: list[PartnerBundle] = []
        for partner in partners:
            bundle = await self.get_bundle(partner.id)
            if bundle is not None:
                bundles.append(bundle)
        return bundles

    def add_service_area(
        self,
        *,
        partner_id: uuid.UUID,
        values: dict[str, object],
    ) -> ServiceArea:
        service_area = ServiceArea(partner_id=partner_id, status="pending", **values)
        self._session.add(service_area)
        return service_area

    async def delete_service_area(
        self,
        *,
        partner_id: uuid.UUID,
        service_area_id: uuid.UUID,
    ) -> bool:
        service_area = await self._session.scalar(
            select(ServiceArea).where(
                ServiceArea.id == service_area_id,
                ServiceArea.partner_id == partner_id,
            )
        )
        if service_area is None:
            return False
        await self._session.delete(service_area)
        return True

    def add_document(
        self,
        *,
        document_id: uuid.UUID,
        partner_id: uuid.UUID,
        uploaded_by_user_id: uuid.UUID,
        values: dict[str, object],
    ) -> PartnerDocument:
        document = PartnerDocument(
            id=document_id,
            partner_id=partner_id,
            object_key=f"quarantine/partners/{partner_id}/documents/{document_id}",
            uploaded_by_user_id=uploaded_by_user_id,
            scan_status="quarantined",
            verification_status="pending",
            **values,
        )
        self._session.add(document)
        return document

    def add_audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        partner_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self._session.add(
            AuditEvent(
                actor_id=actor_id,
                partner_id=partner_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                event_metadata=metadata or {},
            )
        )

    def add_outbox(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        self._session.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
            )
        )

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
