from yoru_api.core.problem import AppError

ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending_payment": frozenset({"paid", "cancelled", "expired"}),
    "paid": frozenset({"processing", "cancelled"}),
    "processing": frozenset({"shipped", "cancelled"}),
    "shipped": frozenset({"delivered"}),
    "delivered": frozenset({"completed"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "expired": frozenset(),
}

PAYMENT_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"succeeded", "failed", "cancelled", "expired"}),
    "requires_action": frozenset({"pending", "succeeded", "failed", "cancelled", "expired"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
    "expired": frozenset(),
}


def ensure_order_transition(current: str, target: str) -> None:
    if target not in ORDER_TRANSITIONS.get(current, frozenset()):
        raise AppError(
            409,
            "ORDER_STATE_CONFLICT",
            "Order state transition is not allowed",
            f"Cannot transition order from '{current}' to '{target}'.",
        )


def ensure_payment_transition(current: str, target: str) -> None:
    if target not in PAYMENT_TRANSITIONS.get(current, frozenset()):
        raise AppError(
            409,
            "PAYMENT_STATE_CONFLICT",
            "Payment state transition is not allowed",
            f"Cannot transition payment from '{current}' to '{target}'.",
        )
