from yoru_api.core.problem import AppError

BOOKING_TRANSITIONS: dict[str, frozenset[str]] = {
    "requested": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"assigned", "cancelled", "no_show"}),
    "assigned": frozenset({"on_the_way", "cancelled", "no_show"}),
    "on_the_way": frozenset({"arrived", "cancelled", "no_show"}),
    "arrived": frozenset({"in_progress", "cancelled", "no_show"}),
    "in_progress": frozenset({"completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "no_show": frozenset(),
}


def ensure_booking_transition(current: str, target: str) -> None:
    allowed = BOOKING_TRANSITIONS.get(current)
    if allowed is None or target not in allowed:
        raise AppError(
            409,
            "BOOKING_STATE_CONFLICT",
            f"Booking cannot transition from {current} to {target}",
        )
