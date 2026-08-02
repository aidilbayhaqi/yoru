from datetime import time

import pytest
from pydantic import ValidationError

from yoru_api.core.problem import AppError
from yoru_api.modules.catalog.domain import (
    available_quantity,
    ensure_inventory_balance,
    slugify,
)
from yoru_api.modules.catalog.schemas import (
    CreateAvailabilityRequest,
    ModerationRequest,
)
from yoru_api.modules.catalog.state_machine import ensure_catalog_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("draft", "pending_review"),
        ("pending_review", "published"),
        ("pending_review", "revision_required"),
        ("pending_review", "rejected"),
        ("revision_required", "pending_review"),
        ("published", "archived"),
        ("archived", "draft"),
    ],
)
def test_valid_catalog_transitions(current: str, target: str) -> None:
    ensure_catalog_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("draft", "published"),
        ("published", "draft"),
        ("rejected", "published"),
        ("archived", "published"),
    ],
)
def test_invalid_catalog_transitions_raise_conflict(current: str, target: str) -> None:
    with pytest.raises(AppError) as error:
        ensure_catalog_transition(current, target)
    assert error.value.status_code == 409
    assert error.value.code == "CATALOG_STATE_CONFLICT"


def test_slugify_normalizes_indonesian_product_name() -> None:
    assert slugify("  Jasa Servis AC Premium  ") == "jasa-servis-ac-premium"


def test_slugify_rejects_symbol_only_value() -> None:
    with pytest.raises(AppError) as error:
        slugify("***")
    assert error.value.code == "CATALOG_SLUG_INVALID"


def test_inventory_available_quantity() -> None:
    assert available_quantity(on_hand=12, reserved=5) == 7


def test_inventory_rejects_reserved_above_on_hand() -> None:
    with pytest.raises(AppError) as error:
        ensure_inventory_balance(on_hand=3, reserved=4)
    assert error.value.code == "INVENTORY_BALANCE_CONFLICT"


def test_availability_requires_end_after_start() -> None:
    with pytest.raises(ValidationError):
        CreateAvailabilityRequest(
            weekday=1,
            start_time=time(17, 0),
            end_time=time(9, 0),
        )


def test_negative_moderation_decision_requires_reason() -> None:
    with pytest.raises(ValidationError):
        ModerationRequest(decision="revision_required")


def test_publish_moderation_does_not_require_reason() -> None:
    payload = ModerationRequest(decision="publish")
    assert payload.reason is None
