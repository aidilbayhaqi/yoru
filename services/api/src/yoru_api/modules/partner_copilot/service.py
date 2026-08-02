import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.identity.permissions import Actor, require_permission
from yoru_api.modules.partner_copilot import ENGINE_VERSION
from yoru_api.modules.partner_copilot.domain import estimate_tokens, generate_insights, grounded_answer, next_weekly_run
from yoru_api.modules.partner_copilot.repository import PartnerCopilotRepository
from yoru_api.modules.partner_copilot.schemas import FeedbackCreate, ScheduleUpdate, SessionCreate, SnapshotRequest


class PartnerCopilotService:
    def __init__(self, repository: PartnerCopilotRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def _enabled(self) -> None:
        if not self._settings.feature_partner_copilot:
            raise AppError(404, "FEATURE_DISABLED", "Partner Copilot is disabled")

    @staticmethod
    def _partner(actor: Actor) -> uuid.UUID:
        if actor.active_partner_id is None:
            raise AppError(409, "ACTIVE_PARTNER_REQUIRED", "Select an active partner before using Partner Copilot")
        return actor.active_partner_id

    async def analyze(self, actor: Actor, payload: SnapshotRequest):
        self._enabled(); partner_id = self._partner(actor)
        require_permission(actor, "partner.copilot.write", partner_id=partner_id, require_partner_write=True)
        end = datetime.now(UTC); start = end - timedelta(days=payload.period_days)
        comparison_end = start; comparison_start = start - timedelta(days=payload.period_days)
        current = await self._repository.collect_metrics(partner_id, start, end)
        previous = await self._repository.collect_metrics(partner_id, comparison_start, comparison_end)
        snapshot = await self._repository.add_snapshot(
            partner_id=partner_id, period_start=start, period_end=end,
            comparison_start=comparison_start, comparison_end=comparison_end,
            currency="IDR", metrics=current, comparison_metrics=previous,
            generated_by_user_id=actor.user_id, engine_version=ENGINE_VERSION,
        )
        now = datetime.now(UTC); insights = []
        for generated in generate_insights(current, previous):
            insights.append(await self._repository.add_insight(
                partner_id=partner_id, snapshot_id=snapshot.id, category=generated.category,
                severity=generated.severity, title=generated.title, summary=generated.summary,
                recommendation=generated.recommendation, evidence=generated.evidence,
                status="active", generated_at=now, dismissed_at=None,
            ))
        self._repository.audit(actor_id=actor.user_id, partner_id=partner_id, action="partner.copilot.analyzed", resource_type="partner_metric_snapshot", resource_id=str(snapshot.id), metadata={"period_days": payload.period_days, "insights": len(insights)})
        self._repository.outbox(aggregate_type="partner_metric_snapshot", aggregate_id=str(snapshot.id), event_type="partner.copilot.snapshot.created", payload={"partner_id": str(partner_id), "snapshot_id": str(snapshot.id)})
        self._repository.add_usage(partner_id=partner_id, user_id=actor.user_id, session_id=None, action="analyze", model_provider="local", model_version=ENGINE_VERSION, input_tokens=0, output_tokens=0, estimated_cost_minor=0, currency="IDR", latency_ms=0, usage_metadata={"period_days": payload.period_days})
        await self._repository.commit(); await self._repository.refresh(snapshot)
        return snapshot, insights

    async def dashboard(self, actor: Actor):
        self._enabled(); partner_id = self._partner(actor)
        require_permission(actor, "partner.copilot.read", partner_id=partner_id)
        snapshot = await self._repository.latest_snapshot(partner_id)
        if snapshot is None: return await self.analyze(actor, SnapshotRequest(period_days=7))
        insights = await self._repository.list_insights(partner_id, "active", 20)
        return snapshot, insights

    async def list_insights(self, actor: Actor, status: str | None, limit: int):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.read", partner_id=partner_id)
        return await self._repository.list_insights(partner_id, status, limit)

    async def dismiss_insight(self, actor: Actor, insight_id: uuid.UUID):
        self._enabled(); partner_id = self._partner(actor)
        require_permission(actor, "partner.copilot.write", partner_id=partner_id, require_partner_write=True)
        item = await self._repository.get_insight(insight_id, for_update=True)
        if item is None or item.partner_id != partner_id: raise AppError(404, "COPILOT_INSIGHT_NOT_FOUND", "Copilot insight was not found")
        item.status = "dismissed"; item.dismissed_at = datetime.now(UTC)
        await self._repository.commit(); await self._repository.refresh(item); return item

    async def create_session(self, actor: Actor, payload: SessionCreate):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.chat", partner_id=partner_id)
        item = await self._repository.add_session(partner_id=partner_id, created_by_user_id=actor.user_id, title=payload.title, status="active", context={})
        await self._repository.commit(); await self._repository.refresh(item); return item

    async def list_sessions(self, actor: Actor, limit: int):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.read", partner_id=partner_id)
        return await self._repository.list_sessions(partner_id, limit)

    async def session_detail(self, actor: Actor, session_id: uuid.UUID):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.read", partner_id=partner_id)
        session = await self._repository.get_session(session_id)
        if session is None or session.partner_id != partner_id: raise AppError(404, "COPILOT_SESSION_NOT_FOUND", "Copilot session was not found")
        return session, await self._repository.list_messages(session.id)

    async def chat(self, actor: Actor, session_id: uuid.UUID, question: str):
        self._enabled(); started = time.perf_counter(); partner_id = self._partner(actor)
        require_permission(actor, "partner.copilot.chat", partner_id=partner_id)
        session = await self._repository.get_session(session_id, for_update=True)
        if session is None or session.partner_id != partner_id: raise AppError(404, "COPILOT_SESSION_NOT_FOUND", "Copilot session was not found")
        if session.status != "active": raise AppError(409, "COPILOT_SESSION_CLOSED", "Copilot session is closed")
        input_tokens = estimate_tokens(question)
        await self._repository.add_message(session_id=session.id, partner_id=partner_id, user_id=actor.user_id, role="user", intent=None, content=question, evidence={}, model_provider="local", model_version=ENGINE_VERSION, input_tokens=input_tokens, output_tokens=0, latency_ms=0)
        snapshot = await self._repository.latest_snapshot(partner_id)
        if snapshot is None:
            snapshot, insights = await self.analyze(actor, SnapshotRequest(period_days=7))
        else:
            insights = await self._repository.list_insights(partner_id, "active", 20)
        insight_dicts = [{"title": i.title, "category": i.category, "severity": i.severity, "evidence": i.evidence} for i in insights]
        intent, answer, evidence = grounded_answer(question, snapshot.metrics, insight_dicts)
        latency = max(0, int((time.perf_counter() - started) * 1000)); output_tokens = estimate_tokens(answer)
        message = await self._repository.add_message(session_id=session.id, partner_id=partner_id, user_id=None, role="assistant", intent=intent, content=answer, evidence=evidence, model_provider="local", model_version=ENGINE_VERSION, input_tokens=input_tokens, output_tokens=output_tokens, latency_ms=latency)
        session.context = {"last_intent": intent, "snapshot_id": str(snapshot.id)}
        self._repository.add_usage(partner_id=partner_id, user_id=actor.user_id, session_id=session.id, action="chat", model_provider="local", model_version=ENGINE_VERSION, input_tokens=input_tokens, output_tokens=output_tokens, estimated_cost_minor=0, currency="IDR", latency_ms=latency, usage_metadata={"intent": intent})
        self._repository.audit(actor_id=actor.user_id, partner_id=partner_id, action="partner.copilot.chat.completed", resource_type="partner_copilot_message", resource_id=str(message.id), metadata={"intent": intent})
        await self._repository.commit(); await self._repository.refresh(message); return message

    async def feedback(self, actor: Actor, message_id: uuid.UUID, payload: FeedbackCreate):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.feedback", partner_id=partner_id)
        message = await self._repository.get_message(message_id)
        if message is None or message.partner_id != partner_id or message.role != "assistant": raise AppError(404, "COPILOT_MESSAGE_NOT_FOUND", "Assistant message was not found")
        try:
            item = await self._repository.add_feedback(message_id=message.id, session_id=message.session_id, partner_id=partner_id, user_id=actor.user_id, rating=payload.rating, helpful=payload.helpful, comment=payload.comment)
            await self._repository.commit(); await self._repository.refresh(item); return item
        except IntegrityError as error:
            raise AppError(409, "COPILOT_FEEDBACK_EXISTS", "Feedback for this message already exists") from error

    async def schedule(self, actor: Actor):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.read", partner_id=partner_id)
        item = await self._repository.get_schedule(partner_id)
        if item is None:
            item = await self._repository.upsert_schedule(partner_id, cadence="weekly", timezone="Asia/Jakarta", weekday=0, hour=8, enabled=False, last_run_at=None, next_run_at=None, updated_by_user_id=actor.user_id)
            await self._repository.commit(); await self._repository.refresh(item)
        return item

    async def update_schedule(self, actor: Actor, payload: ScheduleUpdate):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.write", partner_id=partner_id, require_partner_write=True)
        next_run = next_weekly_run(datetime.now(UTC), weekday=payload.weekday, hour=payload.hour, timezone=payload.timezone) if payload.enabled else None
        item = await self._repository.upsert_schedule(partner_id, cadence="weekly", timezone=payload.timezone, weekday=payload.weekday, hour=payload.hour, enabled=payload.enabled, next_run_at=next_run, updated_by_user_id=actor.user_id)
        await self._repository.commit(); await self._repository.refresh(item); return item

    async def usage(self, actor: Actor):
        self._enabled(); partner_id = self._partner(actor); require_permission(actor, "partner.copilot.read", partner_id=partner_id)
        return await self._repository.usage_summary(partner_id)
