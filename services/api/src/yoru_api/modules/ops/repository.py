import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent, OutboxEvent
from yoru_api.modules.ops.models import LaunchGateEvaluation, OpsJobRun, SecurityEvent


class OpsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def database_probe(self) -> bool:
        try:
            return int(await self._session.scalar(text("SELECT 1")) or 0) == 1
        except Exception:
            return False

    async def current_alembic_head(self) -> str | None:
        try:
            value = await self._session.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
            return str(value) if value else None
        except Exception:
            return None

    async def open_critical_security_events(self) -> int:
        value = await self._session.scalar(
            select(func.count(SecurityEvent.id)).where(
                SecurityEvent.severity == "critical",
                SecurityEvent.status.in_(("open", "acknowledged")),
            )
        )
        return int(value or 0)

    async def latest_successful_job(self, job_type: str) -> OpsJobRun | None:
        return await self._session.scalar(
            select(OpsJobRun)
            .where(OpsJobRun.job_type == job_type, OpsJobRun.status == "completed")
            .order_by(OpsJobRun.completed_at.desc())
            .limit(1)
        )

    async def list_jobs(self, limit: int) -> list[OpsJobRun]:
        return list(
            await self._session.scalars(
                select(OpsJobRun).order_by(OpsJobRun.started_at.desc()).limit(limit)
            )
        )

    async def add_job(self, **values: object) -> OpsJobRun:
        item = OpsJobRun(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def run_retention(self, tracking_retention_days: int) -> dict[str, int]:
        media_result = await self._session.execute(
            text(
                """
                UPDATE ai_media_assets
                SET status='deleted', deleted_at=now()
                WHERE retention_expires_at < now()
                  AND deleted_at IS NULL
                  AND status <> 'deleted'
                """
            )
        )
        ping_result = await self._session.execute(
            text(
                """
                DELETE FROM booking_tracking_pings
                WHERE recorded_at < now() - make_interval(days => :retention_days)
                """
            ),
            {"retention_days": tracking_retention_days},
        )
        session_result = await self._session.execute(
            text(
                """
                UPDATE booking_tracking_sessions
                SET status='expired', stopped_at=COALESCE(stopped_at, now()), updated_at=now()
                WHERE status='active' AND expires_at < now()
                """
            )
        )
        return {
            "ai_media_soft_deleted": max(0, media_result.rowcount or 0),
            "tracking_pings_deleted": max(0, ping_result.rowcount or 0),
            "tracking_sessions_expired": max(0, session_result.rowcount or 0),
        }

    async def add_security_event(self, **values: object) -> SecurityEvent:
        item = SecurityEvent(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_security_events(self, status: str | None, limit: int) -> list[SecurityEvent]:
        statement = select(SecurityEvent).order_by(SecurityEvent.occurred_at.desc()).limit(limit)
        if status is not None:
            statement = statement.where(SecurityEvent.status == status)
        return list(await self._session.scalars(statement))

    async def get_security_event(
        self, event_id: uuid.UUID, *, for_update: bool = False
    ) -> SecurityEvent | None:
        statement = select(SecurityEvent).where(SecurityEvent.id == event_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_launch_evaluation(self, **values: object) -> LaunchGateEvaluation:
        item = LaunchGateEvaluation(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def latest_launch_evaluation(self) -> LaunchGateEvaluation | None:
        return await self._session.scalar(
            select(LaunchGateEvaluation)
            .order_by(LaunchGateEvaluation.evaluated_at.desc())
            .limit(1)
        )

    async def purge_old_security_events(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        result = await self._session.execute(
            text(
                "DELETE FROM security_events WHERE status='resolved' AND resolved_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        return max(0, result.rowcount or 0)

    def audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
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
        payload: dict[str, Any],
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
