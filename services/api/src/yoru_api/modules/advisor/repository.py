import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent, OutboxEvent
from yoru_api.modules.advisor.models import (
    AiAdvisorSession,
    AiConsent,
    AiEvaluationRun,
    AiFeedback,
    AiMediaAsset,
    AiRecommendation,
)
from yoru_api.modules.catalog.models import Product, ServiceOffering


class AdvisorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_consent(self, customer_id: uuid.UUID) -> AiConsent | None:
        return await self._session.scalar(
            select(AiConsent)
            .where(
                AiConsent.customer_id == customer_id,
                AiConsent.scope == "customer_ai",
                AiConsent.status == "active",
            )
            .order_by(AiConsent.created_at.desc())
            .limit(1)
        )

    async def revoke_active_consents(self, customer_id: uuid.UUID, revoked_at: datetime) -> int:
        result = await self._session.scalars(
            select(AiConsent).where(
                AiConsent.customer_id == customer_id,
                AiConsent.scope == "customer_ai",
                AiConsent.status == "active",
            )
        )
        count = 0
        for item in result:
            item.status = "revoked"
            item.revoked_at = revoked_at
            count += 1
        return count

    async def add_consent(self, **values: object) -> AiConsent:
        item = AiConsent(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def add_session(self, **values: object) -> AiAdvisorSession:
        item = AiAdvisorSession(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_session(
        self, session_id: uuid.UUID, *, for_update: bool = False
    ) -> AiAdvisorSession | None:
        statement = select(AiAdvisorSession).where(AiAdvisorSession.id == session_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def list_sessions(
        self, customer_id: uuid.UUID, *, limit: int
    ) -> list[AiAdvisorSession]:
        result = await self._session.scalars(
            select(AiAdvisorSession)
            .where(AiAdvisorSession.customer_id == customer_id)
            .order_by(AiAdvisorSession.created_at.desc(), AiAdvisorSession.id.desc())
            .limit(limit)
        )
        return list(result)

    async def add_media(self, **values: object) -> AiMediaAsset:
        item = AiMediaAsset(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_media(
        self, media_id: uuid.UUID, *, for_update: bool = False
    ) -> AiMediaAsset | None:
        statement = select(AiMediaAsset).where(AiMediaAsset.id == media_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def list_media(self, session_id: uuid.UUID) -> list[AiMediaAsset]:
        result = await self._session.scalars(
            select(AiMediaAsset)
            .where(AiMediaAsset.session_id == session_id)
            .order_by(AiMediaAsset.created_at.asc())
        )
        return list(result)

    async def published_products(self, *, limit: int = 200) -> list[Product]:
        result = await self._session.scalars(
            select(Product)
            .where(Product.status == "published")
            .order_by(Product.updated_at.desc())
            .limit(limit)
        )
        return list(result)

    async def published_services(self, *, limit: int = 200) -> list[ServiceOffering]:
        result = await self._session.scalars(
            select(ServiceOffering)
            .where(ServiceOffering.status == "published")
            .order_by(ServiceOffering.updated_at.desc())
            .limit(limit)
        )
        return list(result)

    async def replace_recommendations(
        self,
        session_id: uuid.UUID,
        items: list[dict[str, object]],
    ) -> list[AiRecommendation]:
        await self._session.execute(
            delete(AiRecommendation).where(AiRecommendation.session_id == session_id)
        )
        output: list[AiRecommendation] = []
        for values in items:
            item = AiRecommendation(**values)
            self._session.add(item)
            output.append(item)
        await self._session.flush()
        return output

    async def list_recommendations(self, session_id: uuid.UUID) -> list[AiRecommendation]:
        result = await self._session.scalars(
            select(AiRecommendation)
            .where(AiRecommendation.session_id == session_id)
            .order_by(AiRecommendation.rank.asc())
        )
        return list(result)

    async def add_feedback(self, **values: object) -> AiFeedback:
        item = AiFeedback(**values)
        self._session.add(item)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise
        return item

    async def add_evaluation(self, **values: object) -> AiEvaluationRun:
        item = AiEvaluationRun(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_evaluations(self, *, limit: int) -> list[AiEvaluationRun]:
        result = await self._session.scalars(
            select(AiEvaluationRun)
            .order_by(AiEvaluationRun.created_at.desc())
            .limit(limit)
        )
        return list(result)

    async def expired_sessions(self, now: datetime, *, limit: int) -> list[AiAdvisorSession]:
        result = await self._session.scalars(
            select(AiAdvisorSession)
            .where(
                AiAdvisorSession.expires_at <= now,
                AiAdvisorSession.status != "expired",
            )
            .order_by(AiAdvisorSession.expires_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result)

    async def minimize_expired_session(self, item: AiAdvisorSession, now: datetime) -> int:
        media = await self.list_media(item.id)
        media_deleted = 0
        for asset in media:
            asset.status = "deleted"
            asset.object_key = f"deleted/{asset.id}"
            asset.original_filename = "deleted"
            asset.scan_result = {}
            asset.deleted_at = now
            media_deleted += 1
        await self._session.execute(
            delete(AiRecommendation).where(AiRecommendation.session_id == item.id)
        )
        await self._session.execute(delete(AiFeedback).where(AiFeedback.session_id == item.id))
        item.goal = "[expired]"
        item.concerns = []
        item.preferences = {}
        item.summary = None
        item.status = "expired"
        return media_deleted

    def audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            AuditEvent(
                actor_id=actor_id,
                partner_id=None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                event_metadata=metadata or {},
            )
        )

    def outbox(
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

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, item: object) -> None:
        await self._session.refresh(item)
