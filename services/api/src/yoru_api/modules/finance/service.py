import uuid
from datetime import UTC, datetime, timedelta
from yoru_api.core.problem import AppError
from yoru_api.modules.commerce.models import Order, PaymentIntent
from yoru_api.modules.finance.domain import COMMISSION_BPS, DISPUTE_TRANSITIONS, PAYOUT_TRANSITIONS, REFUND_TRANSITIONS, SETTLEMENT_HOLD_DAYS, calculate_commission, ensure_balanced, ensure_transition, proportional_commission, reference
from yoru_api.modules.finance.models import Dispute, Payout, Refund, Settlement
from yoru_api.modules.finance.repository import FinanceRepository
from yoru_api.modules.finance.schemas import DisputeCreate, EvidenceCreate, PayoutCreate, ReconciliationCreate, RefundCreate
from yoru_api.modules.identity.permissions import Actor, require_permission

class FinanceService:
    def __init__(self, repository: FinanceRepository): self.r=repository
    @staticmethod
    def now(): return datetime.now(UTC)
    @staticmethod
    def partner(actor):
        if actor.active_partner_id is None: raise AppError(409,'ACTIVE_PARTNER_REQUIRED','Select an active partner')
        return actor.active_partner_id
    async def accounts(self,partner_id,currency):
        clearing=await self.r.ensure_account(code=f'platform:provider_clearing:{currency}',owner_type='platform',owner_id=None,account_type='asset',purpose='provider_clearing',currency=currency,status='active')
        commission=await self.r.ensure_account(code=f'platform:commission:{currency}',owner_type='platform',owner_id=None,account_type='revenue',purpose='platform_commission',currency=currency,status='active')
        pending=await self.r.ensure_account(code=f'partner:{partner_id}:pending:{currency}',owner_type='partner',owner_id=partner_id,account_type='liability',purpose='partner_pending',currency=currency,status='active')
        available=await self.r.ensure_account(code=f'partner:{partner_id}:available:{currency}',owner_type='partner',owner_id=partner_id,account_type='liability',purpose='partner_available',currency=currency,status='active')
        payout=await self.r.ensure_account(code=f'partner:{partner_id}:payout_clearing:{currency}',owner_type='partner',owner_id=partner_id,account_type='liability',purpose='payout_clearing',currency=currency,status='active')
        hold=await self.r.ensure_account(code=f'partner:{partner_id}:dispute_hold:{currency}',owner_type='partner',owner_id=partner_id,account_type='liability',purpose='dispute_hold',currency=currency,status='active')
        return clearing,commission,pending,available,payout,hold
    async def post(self, *, tx_type, currency, description, entries, now, order_id=None,payment_id=None,refund_id=None,payout_id=None,dispute_id=None):
        ensure_balanced([(d,a) for _,d,a,_ in entries])
        tx=await self.r.add_transaction(reference=reference('YTX',now),transaction_type=tx_type,status='posted',order_id=order_id,payment_intent_id=payment_id,refund_id=refund_id,payout_id=payout_id,dispute_id=dispute_id,currency=currency,description=description,transaction_metadata={},posted_at=now)
        for account,direction,amount,partner_id in entries: await self.r.add_entry(transaction_id=tx.id,account_id=account.id,partner_id=partner_id,direction=direction,amount=amount,currency=currency)
        return tx
    async def record_paid_order(self, *, order:Order,payment:PaymentIntent,occurred_at:datetime):
        existing=await self.r.settlement_by_order(order.id,True)
        if existing is not None: return existing
        commission=calculate_commission(order.total_amount); net=order.total_amount-commission
        clearing, revenue, pending,_,_,_=await self.accounts(order.partner_id,order.currency)
        settlement=await self.r.add_settlement(order_id=order.id,payment_intent_id=payment.id,partner_id=order.partner_id,customer_id=order.customer_id,currency=order.currency,gross_amount=order.total_amount,commission_bps=COMMISSION_BPS,commission_amount=commission,net_amount=net,refunded_amount=0,status='pending',available_at=occurred_at+timedelta(days=SETTLEMENT_HOLD_DAYS))
        await self.post(tx_type='sale',currency=order.currency,description=f'Sale settlement for {order.number}',entries=[(clearing,'debit',order.total_amount,None),(pending,'credit',net,order.partner_id),(revenue,'credit',commission,None)],now=occurred_at,order_id=order.id,payment_id=payment.id)
        balance=await self.r.ensure_balance(order.partner_id,order.currency); balance.pending_amount+=net; balance.version+=1
        self.r.audit(None,order.partner_id,'finance.settlement.created','settlement',str(settlement.id),{'order_id':str(order.id)}); self.r.outbox('settlement',str(settlement.id),'finance.settlement.created',{'settlement_id':str(settlement.id),'partner_id':str(order.partner_id)})
        return settlement
    async def backfill(self,actor,order_id):
        require_permission(actor,'platform.finance.manage',require_mfa=True); order=await self.r.get_order(order_id,True)
        if order is None or order.payment_status!='paid': raise AppError(409,'SETTLEMENT_ORDER_INVALID','Order must be paid')
        payment=await self.r.latest_succeeded_payment(order.id)
        if payment is None: raise AppError(409,'SETTLEMENT_PAYMENT_MISSING','Succeeded payment not found')
        item=await self.record_paid_order(order=order,payment=payment,occurred_at=payment.paid_at or self.now()); await self.r.commit(); return item
    async def balance(self,actor):
        pid=self.partner(actor); require_permission(actor,'finance.balance.read',partner_id=pid); item=await self.r.ensure_balance(pid,'IDR'); await self.r.commit(); return item
    async def settlements(self,actor,limit):
        pid=self.partner(actor); require_permission(actor,'finance.balance.read',partner_id=pid); return await self.r.list_settlements(pid,limit)
    async def release(self,actor,settlement_id):
        require_permission(actor,'platform.finance.manage',require_mfa=True); item=await self.r.settlement(settlement_id,True)
        if item is None: raise AppError(404,'SETTLEMENT_NOT_FOUND','Settlement not found')
        if item.status!='pending': raise AppError(409,'SETTLEMENT_STATE_CONFLICT','Settlement is not pending')
        if item.available_at>self.now(): raise AppError(409,'SETTLEMENT_HOLD_ACTIVE','Settlement hold period is active')
        amount=item.net_amount-(item.refunded_amount*item.net_amount//max(1,item.gross_amount)); bal=await self.r.ensure_balance(item.partner_id,item.currency)
        if bal.pending_amount<amount: raise AppError(409,'SETTLEMENT_BALANCE_CONFLICT','Pending balance is insufficient')
        _,_,pending,available,_,_=await self.accounts(item.partner_id,item.currency); now=self.now()
        if amount: await self.post(tx_type='settlement_release',currency=item.currency,description='Release partner settlement',entries=[(pending,'debit',amount,item.partner_id),(available,'credit',amount,item.partner_id)],now=now,order_id=item.order_id)
        bal.pending_amount-=amount; bal.available_amount+=amount; bal.version+=1; item.status='released'; item.released_at=now
        self.r.outbox('settlement',str(item.id),'finance.settlement.released',{'settlement_id':str(item.id)}); await self.r.commit(); return item
    async def create_refund(self,actor,payload:RefundCreate,key):
        existing=await self.r.refund_by_key(key)
        if existing: return existing
        order=await self.r.get_order(payload.order_id)
        if order is None or order.customer_id!=actor.user_id: raise AppError(404,'ORDER_NOT_FOUND','Order not found')
        if order.payment_status not in {'paid','partially_refunded'}: raise AppError(409,'REFUND_ORDER_INVALID','Order is not refundable')
        already=await self.r.refunded_total(order.id)
        if payload.amount>order.total_amount-already: raise AppError(409,'REFUND_AMOUNT_EXCEEDS_REMAINING','Refund exceeds remaining amount')
        payment=await self.r.latest_succeeded_payment(order.id)
        if payment is None: raise AppError(409,'REFUND_PAYMENT_MISSING','Succeeded payment not found')
        now=self.now(); item=await self.r.add_refund(order_id=order.id,payment_intent_id=payment.id,dispute_id=None,customer_id=order.customer_id,partner_id=order.partner_id,requested_by_user_id=actor.user_id,reviewed_by_user_id=None,provider=payment.provider,provider_reference=None,idempotency_key=key,amount=payload.amount,currency=order.currency,status='requested',reason=payload.reason,failure_code=None,requested_at=now,reviewed_at=None,processed_at=None)
        self.r.outbox('refund',str(item.id),'finance.refund.requested',{'refund_id':str(item.id)}); await self.r.commit(); return item
    async def approve_refund(self,actor,item_id):
        require_permission(actor,'platform.finance.manage',require_mfa=True); item=await self.r.refund(item_id,True)
        if item is None: raise AppError(404,'REFUND_NOT_FOUND','Refund not found')
        ensure_transition(item.status,'approved',REFUND_TRANSITIONS,'REFUND_STATE_CONFLICT'); item.status='approved'; item.reviewed_by_user_id=actor.user_id; item.reviewed_at=self.now(); item.provider_reference=f'mock_re_{uuid.uuid4().hex}'; await self.r.commit(); return item
    async def complete_refund(self,actor,item_id,result,failure_code=None):
        require_permission(actor,'platform.finance.manage',require_mfa=True); item=await self.r.refund(item_id,True)
        if item is None: raise AppError(404,'REFUND_NOT_FOUND','Refund not found')
        if item.status=='approved': item.status='processing'
        ensure_transition(item.status,result,REFUND_TRANSITIONS,'REFUND_STATE_CONFLICT')
        now=self.now(); item.status=result; item.processed_at=now; item.failure_code=failure_code
        if result=='succeeded':
            order=await self.r.get_order(item.order_id,True); settlement=await self.r.settlement_by_order(item.order_id,True)
            if order is None or settlement is None: raise AppError(409,'REFUND_SETTLEMENT_MISSING','Settlement is missing')
            commission=proportional_commission(item.amount,settlement.gross_amount,settlement.commission_amount); partner=item.amount-commission; bal=await self.r.ensure_balance(item.partner_id,item.currency)
            clearing,revenue,pending,available,_,hold=await self.accounts(item.partner_id,item.currency); entries=[]
            dispute=await self.r.dispute(item.dispute_id,True) if item.dispute_id else None
            if dispute is not None:
                if bal.held_amount<partner: raise AppError(409,'REFUND_HELD_BALANCE_INSUFFICIENT','Held balance is insufficient')
                entries.append((hold,'debit',partner,item.partner_id)); bal.held_amount-=partner
            else:
                take_pending=min(bal.pending_amount,partner); take_available=partner-take_pending
                if bal.available_amount<take_available: raise AppError(409,'REFUND_BALANCE_INSUFFICIENT','Partner balance is insufficient')
                if take_pending: entries.append((pending,'debit',take_pending,item.partner_id)); bal.pending_amount-=take_pending
                if take_available: entries.append((available,'debit',take_available,item.partner_id)); bal.available_amount-=take_available
            if commission: entries.append((revenue,'debit',commission,None))
            entries.append((clearing,'credit',item.amount,None)); await self.post(tx_type='refund',currency=item.currency,description='Customer refund',entries=entries,now=now,order_id=item.order_id,payment_id=item.payment_intent_id,refund_id=item.id,dispute_id=item.dispute_id)
            bal.version+=1; settlement.refunded_amount+=item.amount; settlement.status='refunded' if settlement.refunded_amount>=settlement.gross_amount else 'partially_refunded'; order.payment_status='refunded' if settlement.status=='refunded' else 'partially_refunded'; order.version+=1
            self.r.outbox('refund',str(item.id),'finance.refund.succeeded',{'refund_id':str(item.id),'order_id':str(order.id)})
        await self.r.commit(); return item
    async def list_refunds(self,actor,limit):
        if actor.active_partner_id: require_permission(actor,'finance.balance.read',partner_id=actor.active_partner_id); return await self.r.list_refunds(partner_id=actor.active_partner_id,limit=limit)
        return await self.r.list_refunds(customer_id=actor.user_id,limit=limit)
    async def request_payout(self,actor,payload:PayoutCreate,key):
        pid=self.partner(actor); require_permission(actor,'finance.payout.create',partner_id=pid); existing=await self.r.payout_by_key(pid,key)
        if existing:return existing
        bal=await self.r.ensure_balance(pid,payload.currency.upper())
        if payload.amount>bal.available_amount: raise AppError(409,'PAYOUT_BALANCE_INSUFFICIENT','Available balance is insufficient')
        now=self.now(); item=await self.r.add_payout(partner_id=pid,requested_by_user_id=actor.user_id,reviewed_by_user_id=None,provider='mock',provider_reference=None,idempotency_key=key,amount=payload.amount,fee_amount=0,currency=payload.currency.upper(),status='requested',destination_snapshot=payload.destination,failure_code=None,requested_at=now,reviewed_at=None,processed_at=None); await self.r.commit(); return item
    async def approve_payout(self,actor,item_id):
        require_permission(actor,'platform.finance.manage',require_mfa=True); item=await self.r.payout(item_id,True)
        if item is None: raise AppError(404,'PAYOUT_NOT_FOUND','Payout not found')
        ensure_transition(item.status,'approved',PAYOUT_TRANSITIONS,'PAYOUT_STATE_CONFLICT'); bal=await self.r.ensure_balance(item.partner_id,item.currency)
        if bal.available_amount<item.amount: raise AppError(409,'PAYOUT_BALANCE_INSUFFICIENT','Available balance is insufficient')
        _,_,_,available,payout,_=await self.accounts(item.partner_id,item.currency); now=self.now(); await self.post(tx_type='payout_hold',currency=item.currency,description='Reserve approved payout',entries=[(available,'debit',item.amount,item.partner_id),(payout,'credit',item.amount,item.partner_id)],now=now,payout_id=item.id)
        bal.available_amount-=item.amount; bal.held_amount+=item.amount; bal.version+=1; item.status='approved'; item.reviewed_by_user_id=actor.user_id; item.reviewed_at=now; item.provider_reference=f'mock_po_{uuid.uuid4().hex}'; await self.r.commit(); return item
    async def complete_payout(self,actor,item_id,result,failure_code=None):
        require_permission(actor,'platform.finance.manage',require_mfa=True); item=await self.r.payout(item_id,True)
        if item is None: raise AppError(404,'PAYOUT_NOT_FOUND','Payout not found')
        if item.status=='approved': item.status='processing'
        ensure_transition(item.status,result,PAYOUT_TRANSITIONS,'PAYOUT_STATE_CONFLICT'); bal=await self.r.ensure_balance(item.partner_id,item.currency); clearing,_,_,available,payout,_=await self.accounts(item.partner_id,item.currency); now=self.now()
        if bal.held_amount<item.amount: raise AppError(409,'PAYOUT_HELD_BALANCE_CONFLICT','Held balance is insufficient')
        if result=='paid': entries=[(payout,'debit',item.amount,item.partner_id),(clearing,'credit',item.amount,None)]; bal.paid_out_amount+=item.amount
        else: entries=[(payout,'debit',item.amount,item.partner_id),(available,'credit',item.amount,item.partner_id)]; bal.available_amount+=item.amount
        await self.post(tx_type='payout' if result=='paid' else 'payout_reversal',currency=item.currency,description='Payout provider result',entries=entries,now=now,payout_id=item.id); bal.held_amount-=item.amount; bal.version+=1; item.status=result; item.failure_code=failure_code; item.processed_at=now; await self.r.commit(); return item
    async def list_payouts(self,actor,limit): pid=self.partner(actor); require_permission(actor,'finance.balance.read',partner_id=pid); return await self.r.list_payouts(pid,limit)
    async def open_dispute(self,actor,payload:DisputeCreate):
        order=await self.r.get_order(payload.order_id,True)
        if order is None or order.customer_id!=actor.user_id: raise AppError(404,'ORDER_NOT_FOUND','Order not found')
        settlement=await self.r.settlement_by_order(order.id,True)
        if settlement is None: raise AppError(409,'DISPUTE_SETTLEMENT_MISSING','Settlement is missing')
        remaining=settlement.gross_amount-settlement.refunded_amount
        if payload.amount>remaining: raise AppError(409,'DISPUTE_AMOUNT_EXCEEDS_REMAINING','Dispute exceeds remaining amount')
        commission=proportional_commission(payload.amount,settlement.gross_amount,settlement.commission_amount); hold_amount=payload.amount-commission; bal=await self.r.ensure_balance(order.partner_id,order.currency); _,_,pending,available,_,hold=await self.accounts(order.partner_id,order.currency); entries=[]
        take_pending=min(bal.pending_amount,hold_amount); take_available=hold_amount-take_pending
        if bal.available_amount<take_available: raise AppError(409,'DISPUTE_BALANCE_INSUFFICIENT','Partner balance cannot be held')
        if take_pending: entries.append((pending,'debit',take_pending,order.partner_id)); bal.pending_amount-=take_pending
        if take_available: entries.append((available,'debit',take_available,order.partner_id)); bal.available_amount-=take_available
        entries.append((hold,'credit',hold_amount,order.partner_id)); now=self.now(); item=await self.r.add_dispute(number=reference('YDP',now),order_id=order.id,settlement_id=settlement.id,customer_id=order.customer_id,partner_id=order.partner_id,opened_by_user_id=actor.user_id,resolved_by_user_id=None,status='open',category=payload.category,amount=payload.amount,partner_hold_amount=hold_amount,currency=order.currency,reason=payload.reason,resolution_notes=None,evidence_due_at=now+timedelta(days=7),resolved_at=None)
        await self.post(tx_type='dispute_hold',currency=order.currency,description='Dispute fund hold',entries=entries,now=now,order_id=order.id,dispute_id=item.id); bal.held_amount+=hold_amount; bal.version+=1; self.r.outbox('dispute',str(item.id),'finance.dispute.opened',{'dispute_id':str(item.id)}); await self.r.commit(); return item
    async def evidence(self,actor,item_id,payload:EvidenceCreate):
        item=await self.r.dispute(item_id)
        if item is None: raise AppError(404,'DISPUTE_NOT_FOUND','Dispute not found')
        if actor.user_id!=item.customer_id:
            if actor.active_partner_id!=item.partner_id: require_permission(actor,'platform.finance.manage')
            else: require_permission(actor,'finance.dispute.respond',partner_id=item.partner_id)
        ev=await self.r.add_evidence(dispute_id=item.id,uploaded_by_user_id=actor.user_id,status='quarantine',**payload.model_dump()); await self.r.commit(); return ev
    async def list_disputes(self,actor,limit):
        if actor.active_partner_id: require_permission(actor,'finance.dispute.respond',partner_id=actor.active_partner_id); return await self.r.list_disputes(partner_id=actor.active_partner_id,limit=limit)
        return await self.r.list_disputes(customer_id=actor.user_id,limit=limit)
    async def resolve(self,actor,item_id,resolution,notes):
        require_permission(actor,'platform.finance.manage',require_mfa=True); item=await self.r.dispute(item_id,True)
        if item is None: raise AppError(404,'DISPUTE_NOT_FOUND','Dispute not found')
        target={'customer':'resolved_customer','partner':'resolved_partner','closed':'closed'}[resolution]; ensure_transition(item.status,target,DISPUTE_TRANSITIONS,'DISPUTE_STATE_CONFLICT'); bal=await self.r.ensure_balance(item.partner_id,item.currency); _,_,pending,available,_,hold=await self.accounts(item.partner_id,item.currency); now=self.now()
        if resolution in {'partner','closed'}:
            destination=pending if (await self.r.settlement(item.settlement_id)).status=='pending' else available; await self.post(tx_type='dispute_release',currency=item.currency,description='Resolve dispute for partner',entries=[(hold,'debit',item.partner_hold_amount,item.partner_id),(destination,'credit',item.partner_hold_amount,item.partner_id)],now=now,order_id=item.order_id,dispute_id=item.id); bal.held_amount-=item.partner_hold_amount; (setattr(bal,'pending_amount',bal.pending_amount+item.partner_hold_amount) if destination is pending else setattr(bal,'available_amount',bal.available_amount+item.partner_hold_amount)); bal.version+=1
        elif resolution=='customer':
            payment=await self.r.latest_succeeded_payment(item.order_id); order=await self.r.get_order(item.order_id)
            if payment is None or order is None: raise AppError(409,'DISPUTE_REFUND_CONTEXT_MISSING','Refund context is missing')
            refund=await self.r.add_refund(order_id=order.id,payment_intent_id=payment.id,dispute_id=item.id,customer_id=item.customer_id,partner_id=item.partner_id,requested_by_user_id=item.opened_by_user_id,reviewed_by_user_id=actor.user_id,provider=payment.provider,provider_reference=f'mock_re_{uuid.uuid4().hex}',idempotency_key=f'dispute:{item.id}',amount=item.amount,currency=item.currency,status='approved',reason=f'Dispute {item.number}: {notes}',failure_code=None,requested_at=now,reviewed_at=now,processed_at=None); self.r.outbox('refund',str(refund.id),'finance.refund.approved',{'refund_id':str(refund.id),'dispute_id':str(item.id)})
        item.status=target; item.resolution_notes=notes; item.resolved_by_user_id=actor.user_id; item.resolved_at=now; await self.r.commit(); return item
    async def reconcile(self,actor,payload:ReconciliationCreate):
        require_permission(actor,'platform.finance.reconcile',require_mfa=True)
        if payload.period_end<=payload.period_start: raise AppError(422,'RECONCILIATION_PERIOD_INVALID','Period end must be after start')
        expected,count=await self.r.provider_totals(payload.provider,payload.period_start,payload.period_end); ledger=await self.r.settlement_total(payload.period_start,payload.period_end); variance=payload.provider_amount-expected; item=await self.r.add_reconciliation(provider=payload.provider,period_start=payload.period_start,period_end=payload.period_end,status='completed',expected_amount=expected,provider_amount=payload.provider_amount,variance_amount=variance,records_checked=count,mismatches=0 if variance==0 and ledger==expected else 1,report={'settlement_total':ledger,'payment_total':expected},created_by_user_id=actor.user_id); await self.r.commit(); return item
    async def ledger(self,actor,limit): pid=self.partner(actor); require_permission(actor,'finance.balance.read',partner_id=pid); return await self.r.list_ledger(pid,limit)
