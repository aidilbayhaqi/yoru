"""Scope refund idempotency keys to the requesting user.

Revision ID: 20260806_0013
Revises: 20260805_0012
Create Date: 2026-08-06
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "20260806_0013"
down_revision: str | None = "20260805_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "refunds"
_OLD_COLUMNS = ("idempotency_key",)
_NEW_COLUMNS = ("requested_by_user_id", "idempotency_key")
_OLD_CONSTRAINT = "uq_refunds_idempotency"
_NEW_CONSTRAINT = "uq_refunds_requester_key"


def _columns(item: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(column) for column in item.get("column_names") or ())


def _unique_objects(
    bind: Connection,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inspector = sa.inspect(bind)
    constraints = [
        item
        for item in inspector.get_unique_constraints(_TABLE)
        if item.get("name")
    ]
    indexes = [
        item
        for item in inspector.get_indexes(_TABLE)
        if item.get("name") and item.get("unique")
    ]
    return constraints, indexes


def _has_unique_columns(
    constraints: list[dict[str, Any]],
    indexes: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> bool:
    return any(_columns(item) == columns for item in (*constraints, *indexes))


def _drop_unique_columns(
    constraints: list[dict[str, Any]],
    indexes: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> None:
    dropped_constraints: set[str] = set()

    for constraint in constraints:
        if _columns(constraint) != columns:
            continue
        name = str(constraint["name"])
        op.drop_constraint(name, _TABLE, type_="unique")
        dropped_constraints.add(name)

    for index in indexes:
        if _columns(index) != columns:
            continue
        name = str(index["name"])
        duplicates_constraint = index.get("duplicates_constraint")
        if name in dropped_constraints or duplicates_constraint in dropped_constraints:
            continue
        op.drop_index(name, table_name=_TABLE)


def _assert_no_duplicates(bind: Connection, columns: tuple[str, ...]) -> None:
    column_sql = ", ".join(columns)
    duplicate = bind.execute(
        sa.text(
            f"""
            SELECT {column_sql}, COUNT(*) AS duplicate_count
            FROM {_TABLE}
            GROUP BY {column_sql}
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot change refund idempotency uniqueness because duplicate rows "
            f"exist for columns {columns!r}. Resolve duplicates before rerunning Alembic."
        )


def upgrade() -> None:
    bind = op.get_bind()
    constraints, indexes = _unique_objects(bind)

    if not _has_unique_columns(constraints, indexes, _NEW_COLUMNS):
        _assert_no_duplicates(bind, _NEW_COLUMNS)
        _drop_unique_columns(constraints, indexes, _OLD_COLUMNS)
        op.create_unique_constraint(
            _NEW_CONSTRAINT,
            _TABLE,
            list(_NEW_COLUMNS),
        )
        return

    # The target uniqueness already exists. Remove a stale global key constraint/index
    # if a previous manual migration left both forms behind.
    _drop_unique_columns(constraints, indexes, _OLD_COLUMNS)


def downgrade() -> None:
    bind = op.get_bind()
    constraints, indexes = _unique_objects(bind)

    if not _has_unique_columns(constraints, indexes, _OLD_COLUMNS):
        _assert_no_duplicates(bind, _OLD_COLUMNS)
        _drop_unique_columns(constraints, indexes, _NEW_COLUMNS)
        op.create_unique_constraint(
            _OLD_CONSTRAINT,
            _TABLE,
            list(_OLD_COLUMNS),
        )
        return

    _drop_unique_columns(constraints, indexes, _NEW_COLUMNS)
