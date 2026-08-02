import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent, OutboxEvent
from yoru_api.modules.bookings.models import Booking
from yoru_api.modules.catalog.models import InventoryItem
from yoru_api.modules.commerce.models import Order
from yoru_api.modules.finance.models import Dispute, Refund, Settlement
from yoru_api.modules.partner_copilot.models import (
    CopilotFeedback, CopilotInsight, CopilotUsageLog, PartnerCopilotMessage,
    PartnerCopilotSchedule, PartnerCopilotSession, PartnerMetricSnapshot,
)


class PartnerCopilotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def collect_metrics(self, partner_id: uuid.UUID, start: datetime, end: datetime) -> dict[str, Any]:
        order_row = (await self._session.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.sum(case((Order.state.in_(("delivered", "completed")), 1), else_=0)), 0),
                func.coalesce(func.sum(case((Order.state == "cancelled", 1), else_=0)), 0),
                func.coalesce(func.sum(case((Order.payment_status.in_(("paid", "partially_refunded", "refunded")), Order.total_amount), else_=0)), 0),
            ).where(Order.partner_id == partner_id, Order.created_at >= start, Order.created_at < end)
        )).one()
        booking_row = (await self._session.execute(
            select(
                func.count(Booking.id),
                func.coalesce(func.sum(case((Booking.status == "completed", 1), else_=0)), 0),
                func.coalesce(func.sum(case((Booking.status == "cancelled", 1), else_=0)), 0),
                func.coalesce(func.sum(case((Booking.status == "no_show", 1), else_=0)), 0),
                func.coalesce(func.sum(case((Booking.status == "completed", Booking.amount), else_=0)), 0),
            ).where(Booking.partner_id == partner_id, Booking.created_at >= start, Booking.created_at < end)
        )).one()
        inventory_row = (await self._session.execute(
            select(
                func.count(InventoryItem.id),
                func.coalesce(func.sum(case(((InventoryItem.on_hand - InventoryItem.reserved) <= InventoryItem.reorder_level, 1), else_=0)), 0),
                func.coalesce(func.sum(case(((InventoryItem.on_hand - InventoryItem.reserved) <= 0, 1), else_=0)), 0),
            ).where(InventoryItem.partner_id == partner_id)
        )).one()
        settlement_row = (await self._session.execute(
            select(
                func.coalesce(func.sum(Settlement.net_amount), 0),
                func.coalesce(func.sum(Settlement.commission_amount), 0),
                func.coalesce(func.sum(case((Settlement.status == "held", Settlement.net_amount - Settlement.refunded_amount), else_=0)), 0),
            ).where(Settlement.partner_id == partner_id, Settlement.created_at >= start, Settlement.created_at < end)
        )).one()
        refund_amount = await self._session.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.partner_id == partner_id, Refund.status == "completed",
                Refund.created_at >= start, Refund.created_at < end,
            )
        )
        open_disputes = await self._session.scalar(
            select(func.count(Dispute.id)).where(
                Dispute.partner_id == partner_id,
                Dispute.status.in_(("open", "under_review", "awaiting_evidence")),
            )
        )
        orders_total = int(order_row[0] or 0)
        gross_revenue = int(order_row[3] or 0) + int(booking_row[4] or 0)
        return {
            "period_start": start.isoformat(), "period_end": end.isoformat(), "currency": "IDR",
            "orders_total": orders_total, "orders_completed": int(order_row[1] or 0),
            "orders_cancelled": int(order_row[2] or 0), "gross_revenue": gross_revenue,
            "average_order_value": int(gross_revenue / orders_total) if orders_total else 0,
            "bookings_total": int(booking_row[0] or 0), "bookings_completed": int(booking_row[1] or 0),
            "bookings_cancelled": int(booking_row[2] or 0), "bookings_no_show": int(booking_row[3] or 0),
            "inventory_total": int(inventory_row[0] or 0), "inventory_low_stock": int(inventory_row[1] or 0),
            "inventory_out_of_stock": int(inventory_row[2] or 0), "net_revenue": int(settlement_row[0] or 0),
            "commission_amount": int(settlement_row[1] or 0), "held_amount": int(settlement_row[2] or 0),
            "refund_amount": int(refund_amount or 0), "open_disputes": int(open_disputes or 0),
        }

    async def add_snapshot(self, **values: object) -> PartnerMetricSnapshot:
        item = PartnerMetricSnapshot(**values); self._session.add(item); await self._session.flush(); return item

    async def latest_snapshot(self, partner_id: uuid.UUID) -> PartnerMetricSnapshot | None:
        return await self._session.scalar(select(PartnerMetricSnapshot).where(PartnerMetricSnapshot.partner_id == partner_id).order_by(PartnerMetricSnapshot.created_at.desc()).limit(1))

    async def add_insight(self, **values: object) -> CopilotInsight:
        item = CopilotInsight(**values); self._session.add(item); await self._session.flush(); return item

    async def list_insights(self, partner_id: uuid.UUID, status: str | None, limit: int) -> list[CopilotInsight]:
        statement = select(CopilotInsight).where(CopilotInsight.partner_id == partner_id).order_by(CopilotInsight.generated_at.desc()).limit(limit)
        if status is not None: statement = statement.where(CopilotInsight.status == status)
        return list(await self._session.scalars(statement))

    async def get_insight(self, insight_id: uuid.UUID, for_update: bool = False) -> CopilotInsight | None:
        statement = select(CopilotInsight).where(CopilotInsight.id == insight_id)
        if for_update: statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_session(self, **values: object) -> PartnerCopilotSession:
        item = PartnerCopilotSession(**values); self._session.add(item); await self._session.flush(); return item

    async def get_session(self, session_id: uuid.UUID, for_update: bool = False) -> PartnerCopilotSession | None:
        statement = select(PartnerCopilotSession).where(PartnerCopilotSession.id == session_id)
        if for_update: statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def list_sessions(self, partner_id: uuid.UUID, limit: int) -> list[PartnerCopilotSession]:
        return list(await self._session.scalars(select(PartnerCopilotSession).where(PartnerCopilotSession.partner_id == partner_id).order_by(PartnerCopilotSession.updated_at.desc()).limit(limit)))

    async def add_message(self, **values: object) -> PartnerCopilotMessage:
        item = PartnerCopilotMessage(**values); self._session.add(item); await self._session.flush(); return item

    async def list_messages(self, session_id: uuid.UUID) -> list[PartnerCopilotMessage]:
        return list(await self._session.scalars(select(PartnerCopilotMessage).where(PartnerCopilotMessage.session_id == session_id).order_by(PartnerCopilotMessage.created_at.asc(), PartnerCopilotMessage.id.asc())))

    async def get_message(self, message_id: uuid.UUID) -> PartnerCopilotMessage | None:
        return await self._session.scalar(select(PartnerCopilotMessage).where(PartnerCopilotMessage.id == message_id))

    async def add_feedback(self, **values: object) -> CopilotFeedback:
        item = CopilotFeedback(**values); self._session.add(item); await self._session.flush(); return item

    def add_usage(self, **values: object) -> CopilotUsageLog:
        item = CopilotUsageLog(**values); self._session.add(item); return item

    async def usage_summary(self, partner_id: uuid.UUID) -> tuple[int, int, int, int]:
        row = (await self._session.execute(select(func.count(CopilotUsageLog.id), func.coalesce(func.sum(CopilotUsageLog.input_tokens), 0), func.coalesce(func.sum(CopilotUsageLog.output_tokens), 0), func.coalesce(func.sum(CopilotUsageLog.estimated_cost_minor), 0)).where(CopilotUsageLog.partner_id == partner_id))).one()
        return tuple(int(value or 0) for value in row)  # type: ignore[return-value]

    async def get_schedule(self, partner_id: uuid.UUID) -> PartnerCopilotSchedule | None:
        return await self._session.scalar(select(PartnerCopilotSchedule).where(PartnerCopilotSchedule.partner_id == partner_id))

    async def upsert_schedule(self, partner_id: uuid.UUID, **values: object) -> PartnerCopilotSchedule:
        item = await self.get_schedule(partner_id)
        if item is None:
            item = PartnerCopilotSchedule(partner_id=partner_id, **values); self._session.add(item); await self._session.flush(); return item
        for key, value in values.items(): setattr(item, key, value)
        await self._session.flush(); return item

    def audit(self, *, actor_id: uuid.UUID | None, partner_id: uuid.UUID | None, action: str, resource_type: str, resource_id: str, metadata: dict[str, Any] | None = None) -> None:
        self._session.add(AuditEvent(actor_id=actor_id, partner_id=partner_id, action=action, resource_type=resource_type, resource_id=resource_id, event_metadata=metadata or {}))

    def outbox(self, *, aggregate_type: str, aggregate_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self._session.add(OutboxEvent(aggregate_type=aggregate_type, aggregate_id=aggregate_id, event_type=event_type, payload=payload))

    async def commit(self) -> None: await self._session.commit()
    async def refresh(self, item: object) -> None: await self._session.refresh(item)
