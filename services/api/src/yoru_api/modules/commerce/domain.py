import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP

from yoru_api.core.problem import AppError

MONEY_SCALE = Decimal("100")


def to_minor_units(value: Decimal) -> int:
    if value < 0:
        raise AppError(422, "MONEY_AMOUNT_INVALID", "Money amount cannot be negative")
    return int((value * MONEY_SCALE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def request_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def calculate_totals(lines: list[tuple[int, int]]) -> dict[str, int]:
    subtotal = sum(unit_amount * quantity for unit_amount, quantity in lines)
    if subtotal < 0:
        raise AppError(422, "CHECKOUT_TOTAL_INVALID", "Checkout total is invalid")
    return {
        "subtotal_amount": subtotal,
        "discount_amount": 0,
        "shipping_amount": 0,
        "tax_amount": 0,
        "total_amount": subtotal,
    }
