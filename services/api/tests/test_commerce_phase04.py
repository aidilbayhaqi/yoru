from decimal import Decimal

import pytest

from yoru_api.core.problem import AppError
from yoru_api.modules.commerce.domain import calculate_totals, request_hash, to_minor_units
from yoru_api.modules.commerce.state_machine import ensure_order_transition, ensure_payment_transition


def test_to_minor_units_uses_decimal_rounding() -> None:
    assert to_minor_units(Decimal("12500.50")) == 1_250_050
    assert to_minor_units(Decimal("0.005")) == 1


def test_calculate_totals() -> None:
    assert calculate_totals([(10_000, 2), (5_500, 1)]) == {
        "subtotal_amount": 25_500,
        "discount_amount": 0,
        "shipping_amount": 0,
        "tax_amount": 0,
        "total_amount": 25_500,
    }


def test_request_hash_is_deterministic() -> None:
    assert request_hash({"b": 2, "a": 1}) == request_hash({"a": 1, "b": 2})


def test_order_state_machine_accepts_expected_transition() -> None:
    ensure_order_transition("pending_payment", "paid")


def test_order_state_machine_rejects_invalid_transition() -> None:
    with pytest.raises(AppError):
        ensure_order_transition("pending_payment", "shipped")


def test_payment_state_machine_rejects_repeated_success() -> None:
    with pytest.raises(AppError):
        ensure_payment_transition("succeeded", "succeeded")
