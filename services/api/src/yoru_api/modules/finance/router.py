from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from yoru_api.core.database import session_scope
from yoru_api.core.problem import AppError
from yoru_api.modules.finance.repository import FinanceRepository
from yoru_api.modules.finance.schemas import BalanceResponse, DisputeCreate, DisputeResponse, EvidenceCreate, EvidenceResponse, LedgerEntryResponse, PayoutCreate, PayoutResponse, ReconciliationCreate, ReconciliationResponse, RefundCreate, RefundResponse, ResolveDispute, ResultRequest, SettlementResponse
from yoru_api.modules.finance.service import FinanceService
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.transport import validate_csrf_or_bearer
router=APIRouter(tags=['Ledger, refund, payout, and dispute'])
async def db(request:Request)->AsyncIterator[AsyncSession]:
 async for s in session_scope(request.app.state.session_factory): yield s
def service(s:Annotated[AsyncSession,Depends(db)])->FinanceService:return FinanceService(FinanceRepository(s))
S=Annotated[FinanceService,Depends(service)]
def csrf(r: Request) -> None:
    validate_csrf_or_bearer(r, csrf_cookie_name=CSRF_COOKIE)

def key(v):
 if v is None or not 8<=len(v)<=120: raise AppError(400,'IDEMPOTENCY_KEY_REQUIRED','A valid Idempotency-Key is required')
 return v
@router.get('/finance/balance',response_model=BalanceResponse)
async def balance(actor:CurrentActor,s:S):return BalanceResponse.model_validate(await s.balance(actor))
@router.get('/finance/settlements',response_model=list[SettlementResponse])
async def settlements(actor:CurrentActor,s:S,limit:int=Query(50,ge=1,le=100)):return [SettlementResponse.model_validate(x) for x in await s.settlements(actor,limit)]
@router.post('/platform/finance/settlements/orders/{order_id}/backfill',response_model=SettlementResponse)
async def backfill(order_id:UUID,r:Request,actor:CurrentActor,s:S):csrf(r);return SettlementResponse.model_validate(await s.backfill(actor,order_id))
@router.post('/platform/finance/settlements/{item_id}/release',response_model=SettlementResponse)
async def release(item_id:UUID,r:Request,actor:CurrentActor,s:S):csrf(r);return SettlementResponse.model_validate(await s.release(actor,item_id))
@router.post('/refunds',response_model=RefundResponse,status_code=status.HTTP_201_CREATED)
async def create_refund(payload:RefundCreate,r:Request,actor:CurrentActor,s:S,idempotency_key:Annotated[str|None,Header(alias='Idempotency-Key')]=None):csrf(r);return RefundResponse.model_validate(await s.create_refund(actor,payload,key(idempotency_key)))
@router.get('/refunds',response_model=list[RefundResponse])
async def refunds(actor:CurrentActor,s:S,limit:int=Query(50,ge=1,le=100)):return [RefundResponse.model_validate(x) for x in await s.list_refunds(actor,limit)]
@router.post('/platform/finance/refunds/{item_id}/approve',response_model=RefundResponse)
async def approve_refund(item_id:UUID,r:Request,actor:CurrentActor,s:S):csrf(r);return RefundResponse.model_validate(await s.approve_refund(actor,item_id))
@router.post('/platform/finance/refunds/{item_id}/complete',response_model=RefundResponse)
async def complete_refund(item_id:UUID,payload:ResultRequest,r:Request,actor:CurrentActor,s:S):csrf(r);return RefundResponse.model_validate(await s.complete_refund(actor,item_id,payload.result,payload.failure_code))
@router.post('/finance/payouts',response_model=PayoutResponse,status_code=status.HTTP_201_CREATED)
async def request_payout(payload:PayoutCreate,r:Request,actor:CurrentActor,s:S,idempotency_key:Annotated[str|None,Header(alias='Idempotency-Key')]=None):csrf(r);return PayoutResponse.model_validate(await s.request_payout(actor,payload,key(idempotency_key)))
@router.get('/finance/payouts',response_model=list[PayoutResponse])
async def payouts(actor:CurrentActor,s:S,limit:int=Query(50,ge=1,le=100)):return [PayoutResponse.model_validate(x) for x in await s.list_payouts(actor,limit)]
@router.post('/platform/finance/payouts/{item_id}/approve',response_model=PayoutResponse)
async def approve_payout(item_id:UUID,r:Request,actor:CurrentActor,s:S):csrf(r);return PayoutResponse.model_validate(await s.approve_payout(actor,item_id))
@router.post('/platform/finance/payouts/{item_id}/complete',response_model=PayoutResponse)
async def complete_payout(item_id:UUID,payload:ResultRequest,r:Request,actor:CurrentActor,s:S):csrf(r);return PayoutResponse.model_validate(await s.complete_payout(actor,item_id,payload.result,payload.failure_code))
@router.post('/disputes',response_model=DisputeResponse,status_code=status.HTTP_201_CREATED)
async def open_dispute(payload:DisputeCreate,r:Request,actor:CurrentActor,s:S):csrf(r);return DisputeResponse.model_validate(await s.open_dispute(actor,payload))
@router.get('/disputes',response_model=list[DisputeResponse])
async def disputes(actor:CurrentActor,s:S,limit:int=Query(50,ge=1,le=100)):return [DisputeResponse.model_validate(x) for x in await s.list_disputes(actor,limit)]
@router.post('/disputes/{item_id}/evidence',response_model=EvidenceResponse,status_code=status.HTTP_201_CREATED)
async def evidence(item_id:UUID,payload:EvidenceCreate,r:Request,actor:CurrentActor,s:S):csrf(r);return EvidenceResponse.model_validate(await s.evidence(actor,item_id,payload))
@router.post('/platform/finance/disputes/{item_id}/resolve',response_model=DisputeResponse)
async def resolve(item_id:UUID,payload:ResolveDispute,r:Request,actor:CurrentActor,s:S):csrf(r);return DisputeResponse.model_validate(await s.resolve(actor,item_id,payload.resolution,payload.notes))
@router.post('/platform/finance/reconciliation',response_model=ReconciliationResponse,status_code=status.HTTP_201_CREATED)
async def reconcile(payload:ReconciliationCreate,r:Request,actor:CurrentActor,s:S):csrf(r);return ReconciliationResponse.model_validate(await s.reconcile(actor,payload))
@router.get('/finance/ledger',response_model=list[LedgerEntryResponse])
async def ledger(actor:CurrentActor,s:S,limit:int=Query(100,ge=1,le=500)):return [LedgerEntryResponse.model_validate(x) for x in await s.ledger(actor,limit)]
