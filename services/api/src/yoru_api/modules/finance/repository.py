import uuid
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from yoru_api.core.models import AuditEvent, OutboxEvent
from yoru_api.modules.commerce.models import Order, PaymentIntent
from yoru_api.modules.finance.models import Dispute, DisputeEvidence, LedgerAccount, LedgerEntry, LedgerTransaction, PartnerBalance, Payout, ReconciliationRun, Refund, Settlement

class FinanceRepository:
    def __init__(self, session: AsyncSession) -> None: self._session=session
    @property
    def session(self) -> AsyncSession: return self._session
    async def get_order(self, item_id, for_update=False):
        s=select(Order).where(Order.id==item_id); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def get_payment(self, item_id, for_update=False):
        s=select(PaymentIntent).where(PaymentIntent.id==item_id); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def latest_succeeded_payment(self, order_id):
        return await self._session.scalar(select(PaymentIntent).where(PaymentIntent.order_id==order_id, PaymentIntent.status=='succeeded').order_by(PaymentIntent.paid_at.desc()).limit(1))
    async def account(self, code): return await self._session.scalar(select(LedgerAccount).where(LedgerAccount.code==code))
    async def ensure_account(self, **v):
        item=await self.account(v['code'])
        if item is None: item=LedgerAccount(**v); self._session.add(item); await self._session.flush()
        return item
    async def balance(self, partner_id, currency, for_update=False):
        s=select(PartnerBalance).where(PartnerBalance.partner_id==partner_id, PartnerBalance.currency==currency); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def ensure_balance(self, partner_id, currency):
        item=await self.balance(partner_id,currency,True)
        if item is None: item=PartnerBalance(partner_id=partner_id,currency=currency,pending_amount=0,available_amount=0,held_amount=0,paid_out_amount=0,version=1); self._session.add(item); await self._session.flush()
        return item
    async def settlement_by_order(self, order_id, for_update=False):
        s=select(Settlement).where(Settlement.order_id==order_id); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def settlement(self, item_id, for_update=False):
        s=select(Settlement).where(Settlement.id==item_id); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def list_settlements(self, partner_id, limit): return list(await self._session.scalars(select(Settlement).where(Settlement.partner_id==partner_id).order_by(Settlement.created_at.desc()).limit(limit)))
    async def add_settlement(self, **v): item=Settlement(**v); self._session.add(item); await self._session.flush(); return item
    async def add_transaction(self, **v): item=LedgerTransaction(**v); self._session.add(item); await self._session.flush(); return item
    async def add_entry(self, **v): item=LedgerEntry(**v); self._session.add(item); await self._session.flush(); return item
    async def list_ledger(self, partner_id, limit): return list(await self._session.scalars(select(LedgerEntry).where(LedgerEntry.partner_id==partner_id).order_by(LedgerEntry.created_at.desc()).limit(limit)))
    async def refund(self,item_id,for_update=False):
        s=select(Refund).where(Refund.id==item_id); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def refund_by_key(self, requested_by_user_id, key):
        return await self._session.scalar(
            select(Refund).where(
                Refund.requested_by_user_id == requested_by_user_id,
                Refund.idempotency_key == key,
            )
        )
    async def add_refund(self,**v): item=Refund(**v); self._session.add(item); await self._session.flush(); return item
    async def list_refunds(self, customer_id=None, partner_id=None, limit=50):
        s=select(Refund); s=s.where(Refund.customer_id==customer_id) if customer_id else s; s=s.where(Refund.partner_id==partner_id) if partner_id else s
        return list(await self._session.scalars(s.order_by(Refund.created_at.desc()).limit(limit)))
    async def refunded_total(self,order_id): return int((await self._session.scalar(select(func.coalesce(func.sum(Refund.amount),0)).where(Refund.order_id==order_id,Refund.status=='succeeded'))) or 0)
    async def payout(self,item_id,for_update=False):
        s=select(Payout).where(Payout.id==item_id); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def payout_by_key(self,partner_id,key): return await self._session.scalar(select(Payout).where(Payout.partner_id==partner_id,Payout.idempotency_key==key))
    async def add_payout(self,**v): item=Payout(**v); self._session.add(item); await self._session.flush(); return item
    async def list_payouts(self,partner_id,limit): return list(await self._session.scalars(select(Payout).where(Payout.partner_id==partner_id).order_by(Payout.created_at.desc()).limit(limit)))
    async def dispute(self,item_id,for_update=False):
        s=select(Dispute).where(Dispute.id==item_id); s=s.with_for_update() if for_update else s; return await self._session.scalar(s)
    async def add_dispute(self,**v): item=Dispute(**v); self._session.add(item); await self._session.flush(); return item
    async def list_disputes(self,customer_id=None,partner_id=None,limit=50):
        s=select(Dispute); s=s.where(Dispute.customer_id==customer_id) if customer_id else s; s=s.where(Dispute.partner_id==partner_id) if partner_id else s
        return list(await self._session.scalars(s.order_by(Dispute.created_at.desc()).limit(limit)))
    async def add_evidence(self,**v): item=DisputeEvidence(**v); self._session.add(item); await self._session.flush(); return item
    async def list_evidence(self,dispute_id): return list(await self._session.scalars(select(DisputeEvidence).where(DisputeEvidence.dispute_id==dispute_id).order_by(DisputeEvidence.created_at)))
    async def provider_totals(self,provider,start,end):
        s=select(func.coalesce(func.sum(PaymentIntent.amount),0),func.count(PaymentIntent.id)).where(PaymentIntent.provider==provider,PaymentIntent.status=='succeeded',PaymentIntent.paid_at>=start,PaymentIntent.paid_at<end)
        row=(await self._session.execute(s)).one(); return int(row[0]),int(row[1])
    async def settlement_total(self,start,end): return int((await self._session.scalar(select(func.coalesce(func.sum(Settlement.gross_amount),0)).where(Settlement.created_at>=start,Settlement.created_at<end))) or 0)
    async def add_reconciliation(self,**v): item=ReconciliationRun(**v); self._session.add(item); await self._session.flush(); return item
    def audit(self,actor_id,partner_id,action,resource_type,resource_id,metadata=None): self._session.add(AuditEvent(actor_id=actor_id,partner_id=partner_id,action=action,resource_type=resource_type,resource_id=resource_id,event_metadata=metadata or {}))
    def outbox(self,aggregate_type,aggregate_id,event_type,payload): self._session.add(OutboxEvent(aggregate_type=aggregate_type,aggregate_id=aggregate_id,event_type=event_type,payload=payload))
    async def rollback(self):
        await self._session.rollback()
    async def commit(self): await self._session.commit()
