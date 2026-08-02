from datetime import UTC, datetime
import pytest
from yoru_api.core.problem import AppError
from yoru_api.modules.finance.domain import calculate_commission, ensure_balanced, proportional_commission, reference

def test_commission_and_proportional_refund():
 assert calculate_commission(100_000)==10_000
 assert proportional_commission(50_000,100_000,10_000)==5_000

def test_balanced_entries_are_accepted(): ensure_balanced([('debit',100),('credit',60),('credit',40)])
def test_unbalanced_entries_are_rejected():
 with pytest.raises(AppError) as e: ensure_balanced([('debit',100),('credit',99)])
 assert e.value.code=='LEDGER_UNBALANCED'
def test_reference_prefix(): assert reference('YTX',datetime(2026,8,1,tzinfo=UTC)).startswith('YTX-20260801-')
