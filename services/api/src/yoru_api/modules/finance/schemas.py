from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class BalanceResponse(ORM): partner_id:UUID; currency:str; pending_amount:int; available_amount:int; held_amount:int; paid_out_amount:int; version:int
class SettlementResponse(ORM): id:UUID; order_id:UUID; payment_intent_id:UUID; partner_id:UUID; currency:str; gross_amount:int; commission_bps:int; commission_amount:int; net_amount:int; refunded_amount:int; status:str; available_at:datetime; released_at:datetime|None
class RefundCreate(BaseModel): order_id:UUID; amount:int=Field(gt=0); reason:str=Field(min_length=5,max_length=1000)
class RefundResponse(ORM): id:UUID; order_id:UUID; customer_id:UUID; partner_id:UUID; provider:str; provider_reference:str|None; amount:int; currency:str; status:str; reason:str; failure_code:str|None; requested_at:datetime; reviewed_at:datetime|None; processed_at:datetime|None
class ResultRequest(BaseModel): result:Literal['succeeded','failed']; failure_code:str|None=None
class PayoutCreate(BaseModel): amount:int=Field(gt=0); currency:str=Field(default='IDR',min_length=3,max_length=3); destination:dict[str,Any]
class PayoutResponse(ORM): id:UUID; partner_id:UUID; provider:str; provider_reference:str|None; amount:int; fee_amount:int; currency:str; status:str; destination_snapshot:dict[str,Any]; failure_code:str|None; requested_at:datetime; reviewed_at:datetime|None; processed_at:datetime|None
class DisputeCreate(BaseModel): order_id:UUID; category:str=Field(min_length=3,max_length=80); amount:int=Field(gt=0); reason:str=Field(min_length=10,max_length=2000)
class EvidenceCreate(BaseModel): kind:str=Field(min_length=2,max_length=50); storage_key:str=Field(min_length=5,max_length=500); sha256:str=Field(pattern=r'^[0-9a-fA-F]{64}$'); content_type:str=Field(min_length=3,max_length=120); description:str|None=Field(default=None,max_length=1000)
class EvidenceResponse(ORM): id:UUID; dispute_id:UUID; kind:str; storage_key:str; sha256:str; content_type:str; description:str|None; status:str; created_at:datetime
class DisputeResponse(ORM): id:UUID; number:str; order_id:UUID; customer_id:UUID; partner_id:UUID; status:str; category:str; amount:int; partner_hold_amount:int; currency:str; reason:str; resolution_notes:str|None; evidence_due_at:datetime|None; resolved_at:datetime|None
class ResolveDispute(BaseModel): resolution:Literal['customer','partner','closed']; notes:str=Field(min_length=5,max_length=2000)
class ReconciliationCreate(BaseModel): provider:str=Field(default='mock',min_length=2,max_length=50); period_start:datetime; period_end:datetime; provider_amount:int=Field(ge=0)
class ReconciliationResponse(ORM): id:UUID; provider:str; period_start:datetime; period_end:datetime; status:str; expected_amount:int; provider_amount:int; variance_amount:int; records_checked:int; mismatches:int; report:dict[str,Any]; created_at:datetime
class LedgerEntryResponse(ORM): id:UUID; transaction_id:UUID; account_id:UUID; partner_id:UUID|None; direction:str; amount:int; currency:str; created_at:datetime
