import secrets
from datetime import datetime

from yoru_api.core.problem import AppError

COMMISSION_BPS = 1000
SETTLEMENT_HOLD_DAYS = 7


def calculate_commission(gross_amount: int, basis_points: int = COMMISSION_BPS) -> int:
    if gross_amount < 0 or not 0 <= basis_points <= 5000:
        raise AppError(422, "FINANCE_COMMISSION_INVALID", "Commission input is invalid")
    return (gross_amount * basis_points) // 10_000


def proportional_commission(amount: int, gross_amount: int, commission_amount: int) -> int:
    if amount <= 0 or gross_amount <= 0 or amount > gross_amount:
        raise AppError(422, "REFUND_AMOUNT_INVALID", "Refund amount is invalid")
    return min(commission_amount, (amount * commission_amount) // gross_amount)


def ensure_balanced(entries: list[tuple[str, int]]) -> None:
    if not entries or any(direction not in {"debit", "credit"} or amount <= 0 for direction, amount in entries):
        raise AppError(422, "LEDGER_ENTRY_INVALID", "Ledger entries are invalid")
    debits = sum(amount for direction, amount in entries if direction == "debit")
    credits = sum(amount for direction, amount in entries if direction == "credit")
    if debits != credits:
        raise AppError(409, "LEDGER_UNBALANCED", "Ledger transaction is not balanced")


def reference(prefix: str, now: datetime) -> str:
    return f"{prefix}-{now:%Y%m%d}-{secrets.token_hex(4).upper()}"


def ensure_transition(current: str, target: str, transitions: dict[str, set[str]], code: str) -> None:
    if target not in transitions.get(current, set()):
        raise AppError(409, code, f"Transition from {current} to {target} is not allowed")

REFUND_TRANSITIONS = {
    "requested": {"approved", "cancelled"},
    "approved": {"processing", "cancelled"},
    "processing": {"succeeded", "failed"},
    "failed": {"processing", "cancelled"},
}
PAYOUT_TRANSITIONS = {
    "requested": {"approved", "cancelled"},
    "approved": {"processing", "cancelled"},
    "processing": {"paid", "failed"},
    "failed": {"processing", "cancelled"},
}
DISPUTE_TRANSITIONS = {
    "open": {"under_review", "awaiting_evidence", "resolved_customer", "resolved_partner", "closed"},
    "under_review": {"awaiting_evidence", "resolved_customer", "resolved_partner", "closed"},
    "awaiting_evidence": {"under_review", "resolved_customer", "resolved_partner", "closed"},
}
