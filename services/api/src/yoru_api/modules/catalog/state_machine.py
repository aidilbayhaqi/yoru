from yoru_api.core.problem import AppError

CATALOG_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"pending_review", "archived"}),
    "pending_review": frozenset({"published", "revision_required", "rejected"}),
    "published": frozenset({"archived"}),
    "revision_required": frozenset({"pending_review", "archived"}),
    "rejected": frozenset({"draft", "archived"}),
    "archived": frozenset({"draft"}),
}


def ensure_catalog_transition(current: str, target: str) -> None:
    allowed = CATALOG_TRANSITIONS.get(current)
    if allowed is None or target not in allowed:
        raise AppError(
            409,
            "CATALOG_STATE_CONFLICT",
            "Catalog state transition is not allowed",
            f"Cannot transition catalog item from '{current}' to '{target}'.",
        )
