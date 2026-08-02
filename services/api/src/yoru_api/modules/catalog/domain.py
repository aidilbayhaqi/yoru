import re
import unicodedata

from yoru_api.core.problem import AppError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = _SLUG_PATTERN.sub("-", normalized.lower()).strip("-")
    if not slug:
        raise AppError(422, "CATALOG_SLUG_INVALID", "Catalog slug is invalid")
    return slug[:200]


def ensure_inventory_balance(*, on_hand: int, reserved: int) -> None:
    if on_hand < 0 or reserved < 0:
        raise AppError(
            422,
            "INVENTORY_QUANTITY_INVALID",
            "Inventory quantities cannot be negative",
        )
    if reserved > on_hand:
        raise AppError(
            409,
            "INVENTORY_BALANCE_CONFLICT",
            "Reserved quantity cannot exceed on-hand quantity",
        )


def available_quantity(*, on_hand: int, reserved: int) -> int:
    ensure_inventory_balance(on_hand=on_hand, reserved=reserved)
    return on_hand - reserved
