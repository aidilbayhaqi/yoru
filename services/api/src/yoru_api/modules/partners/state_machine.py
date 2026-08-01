from yoru_api.core.problem import AppError

PARTNER_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"submitted"}),
    "submitted": frozenset({"under_review"}),
    "under_review": frozenset({"revision_required", "verified", "rejected"}),
    "revision_required": frozenset({"submitted"}),
    "verified": frozenset({"suspended", "closed"}),
    "suspended": frozenset({"verified"}),
    "rejected": frozenset(),
    "closed": frozenset(),
}


def ensure_partner_transition(current: str, target: str) -> None:
    allowed = PARTNER_TRANSITIONS.get(current)
    if allowed is None or target not in allowed:
        raise AppError(
            409,
            "PARTNER_STATE_CONFLICT",
            "Partner state transition is not allowed",
            f"Cannot transition partner from '{current}' to '{target}'.",
        )
