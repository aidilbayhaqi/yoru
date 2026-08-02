import time
import uuid
from datetime import UTC, datetime

from yoru_api import __version__
from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.identity.permissions import Actor, require_permission
from yoru_api.modules.ops.domain import evaluate_launch_gates
from yoru_api.modules.ops.repository import OpsRepository
from yoru_api.modules.ops.schemas import RestoreDrillCreate, SecurityEventCreate, SecurityEventResolve

EXPECTED_ALEMBIC_HEAD = "20260802_0010"


class OpsService:
    def __init__(self, repository: OpsRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def _gate_inputs(self) -> tuple[bool, str | None, int, datetime | None]:
        database_ok = await self._repository.database_probe()
        current_head = await self._repository.current_alembic_head()
        critical_events = await self._repository.open_critical_security_events()
        restore_job = await self._repository.latest_successful_job("restore_drill")
        restore_at = restore_job.completed_at if restore_job else None
        return database_ok, current_head, critical_events, restore_at

    async def readiness(self, actor: Actor) -> dict[str, object]:
        require_permission(actor, "platform.ops.read")
        database_ok, current_head, critical_events, restore_at = await self._gate_inputs()
        status, checks = evaluate_launch_gates(
            app_env=self._settings.app_env,
            docs_enabled=self._settings.docs_enabled,
            cookie_secure=self._settings.cookie_secure,
            database_ok=database_ok,
            current_alembic_head=current_head,
            expected_alembic_head=EXPECTED_ALEMBIC_HEAD,
            open_critical_security_events=critical_events,
            last_restore_drill_at=restore_at,
            restore_drill_max_age_days=self._settings.restore_drill_max_age_days,
        )
        return {
            "status": status,
            "release_version": __version__,
            "current_alembic_head": current_head,
            "checks": checks,
        }

    async def list_jobs(self, actor: Actor, limit: int):
        require_permission(actor, "platform.ops.read")
        return await self._repository.list_jobs(limit)

    async def run_retention(self, actor: Actor):
        require_permission(actor, "platform.ops.manage")
        started = datetime.now(UTC)
        job = await self._repository.add_job(
            job_type="retention",
            status="running",
            started_by_user_id=actor.user_id,
            started_at=started,
            completed_at=None,
            duration_ms=None,
            summary={},
            error_message=None,
        )
        await self._repository.commit()
        started_clock = time.perf_counter()
        try:
            results = await self._repository.run_retention(
                self._settings.tracking_retention_days
            )
            results["security_events_deleted"] = await self._repository.purge_old_security_events(
                self._settings.security_event_retention_days
            )
            job.status = "completed"
            job.summary = results
            job.completed_at = datetime.now(UTC)
            job.duration_ms = max(0, int((time.perf_counter() - started_clock) * 1000))
            self._repository.audit(
                actor_id=actor.user_id,
                action="platform.ops.retention.completed",
                resource_type="ops_job_run",
                resource_id=str(job.id),
                metadata=results,
            )
            self._repository.outbox(
                aggregate_type="ops_job_run",
                aggregate_id=str(job.id),
                event_type="platform.ops.retention.completed",
                payload=results,
            )
            await self._repository.commit()
            await self._repository.refresh(job)
            return job, results
        except Exception as error:
            job.status = "failed"
            job.completed_at = datetime.now(UTC)
            job.duration_ms = max(0, int((time.perf_counter() - started_clock) * 1000))
            job.error_message = str(error)[:4000]
            await self._repository.commit()
            raise

    async def record_restore_drill(self, actor: Actor, payload: RestoreDrillCreate):
        require_permission(actor, "platform.ops.manage")
        now = datetime.now(UTC)
        summary = {
            "backup_reference": payload.backup_reference,
            "restored_database": payload.restored_database,
            "notes": payload.notes,
        }
        job = await self._repository.add_job(
            job_type="restore_drill",
            status="completed" if payload.successful else "failed",
            started_by_user_id=actor.user_id,
            started_at=now,
            completed_at=now,
            duration_ms=payload.duration_ms,
            summary=summary,
            error_message=None if payload.successful else (payload.notes or "Restore drill failed"),
        )
        self._repository.audit(
            actor_id=actor.user_id,
            action="platform.ops.restore_drill.recorded",
            resource_type="ops_job_run",
            resource_id=str(job.id),
            metadata={"successful": payload.successful, **summary},
        )
        await self._repository.commit()
        await self._repository.refresh(job)
        return job

    async def create_security_event(self, actor: Actor, payload: SecurityEventCreate):
        require_permission(actor, "platform.security.manage")
        item = await self._repository.add_security_event(
            severity=payload.severity,
            event_type=payload.event_type,
            source=payload.source,
            status="open",
            actor_user_id=actor.user_id,
            request_id=payload.request_id,
            ip_prefix=payload.ip_prefix,
            description=payload.description,
            event_metadata=payload.metadata,
            occurred_at=datetime.now(UTC),
            acknowledged_at=None,
            resolved_at=None,
            resolved_by_user_id=None,
            resolution_note=None,
        )
        self._repository.audit(
            actor_id=actor.user_id,
            action="platform.security.event.created",
            resource_type="security_event",
            resource_id=str(item.id),
            metadata={"severity": item.severity, "event_type": item.event_type},
        )
        await self._repository.commit()
        await self._repository.refresh(item)
        return item

    async def list_security_events(self, actor: Actor, status: str | None, limit: int):
        require_permission(actor, "platform.security.read")
        return await self._repository.list_security_events(status, limit)

    async def resolve_security_event(
        self,
        actor: Actor,
        event_id: uuid.UUID,
        payload: SecurityEventResolve,
    ):
        require_permission(actor, "platform.security.manage")
        item = await self._repository.get_security_event(event_id, for_update=True)
        if item is None:
            raise AppError(404, "SECURITY_EVENT_NOT_FOUND", "Security event was not found")
        now = datetime.now(UTC)
        item.status = payload.status
        item.resolution_note = payload.note
        item.resolved_by_user_id = actor.user_id
        if payload.status == "acknowledged":
            item.acknowledged_at = now
        else:
            item.resolved_at = now
            item.acknowledged_at = item.acknowledged_at or now
        self._repository.audit(
            actor_id=actor.user_id,
            action=f"platform.security.event.{payload.status}",
            resource_type="security_event",
            resource_id=str(item.id),
            metadata={"note": payload.note},
        )
        await self._repository.commit()
        await self._repository.refresh(item)
        return item

    async def evaluate_launch_gate(self, actor: Actor):
        require_permission(actor, "platform.ops.manage")
        database_ok, current_head, critical_events, restore_at = await self._gate_inputs()
        status, checks = evaluate_launch_gates(
            app_env=self._settings.app_env,
            docs_enabled=self._settings.docs_enabled,
            cookie_secure=self._settings.cookie_secure,
            database_ok=database_ok,
            current_alembic_head=current_head,
            expected_alembic_head=EXPECTED_ALEMBIC_HEAD,
            open_critical_security_events=critical_events,
            last_restore_drill_at=restore_at,
            restore_drill_max_age_days=self._settings.restore_drill_max_age_days,
        )
        item = await self._repository.add_launch_evaluation(
            release_version=__version__,
            expected_alembic_head=EXPECTED_ALEMBIC_HEAD,
            status=status,
            checks=checks,
            evaluated_by_user_id=actor.user_id,
            evaluated_at=datetime.now(UTC),
        )
        self._repository.audit(
            actor_id=actor.user_id,
            action="platform.ops.launch_gate.evaluated",
            resource_type="launch_gate_evaluation",
            resource_id=str(item.id),
            metadata={"status": status},
        )
        await self._repository.commit()
        await self._repository.refresh(item)
        return item

    async def latest_launch_gate(self, actor: Actor):
        require_permission(actor, "platform.ops.read")
        item = await self._repository.latest_launch_evaluation()
        if item is None:
            raise AppError(404, "LAUNCH_GATE_NOT_FOUND", "No launch-gate evaluation exists")
        return item
