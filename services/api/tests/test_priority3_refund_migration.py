from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


def _load_migration() -> ModuleType:
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260806_0013_scope_refund_idempotency.py"
    )
    spec = importlib.util.spec_from_file_location("refund_idempotency_0013", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Result:
    def __init__(self, row: object | None = None) -> None:
        self._row = row

    def first(self) -> object | None:
        return self._row


class _Bind:
    def __init__(self, duplicate: object | None = None) -> None:
        self.duplicate = duplicate
        self.statements: list[str] = []

    def execute(self, statement: Any) -> _Result:
        self.statements.append(str(statement))
        return _Result(self.duplicate)


class _Inspector:
    def __init__(
        self,
        constraints: list[dict[str, Any]],
        indexes: list[dict[str, Any]] | None = None,
    ) -> None:
        self.constraints = constraints
        self.indexes = indexes or []

    def get_unique_constraints(self, table_name: str) -> list[dict[str, Any]]:
        assert table_name == "refunds"
        return self.constraints

    def get_indexes(self, table_name: str) -> list[dict[str, Any]]:
        assert table_name == "refunds"
        return self.indexes


def test_upgrade_drops_auto_named_legacy_constraint(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _load_migration()
    bind = _Bind()
    inspector = _Inspector(
        constraints=[
            {
                "name": "refunds_idempotency_key_key",
                "column_names": ["idempotency_key"],
            }
        ],
        indexes=[
            {
                "name": "refunds_idempotency_key_key",
                "column_names": ["idempotency_key"],
                "unique": True,
                "duplicates_constraint": "refunds_idempotency_key_key",
            }
        ],
    )
    calls: list[tuple[object, ...]] = []

    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration.op,
        "drop_constraint",
        lambda *args, **kwargs: calls.append(("drop_constraint", *args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_index",
        lambda *args, **kwargs: calls.append(("drop_index", *args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "create_unique_constraint",
        lambda *args, **kwargs: calls.append(("create", *args, kwargs)),
    )

    migration.upgrade()

    assert (
        "drop_constraint",
        "refunds_idempotency_key_key",
        "refunds",
        {"type_": "unique"},
    ) in calls
    assert not any(call[0] == "drop_index" for call in calls)
    assert (
        "create",
        "uq_refunds_requester_key",
        "refunds",
        ["requested_by_user_id", "idempotency_key"],
        {},
    ) in calls


def test_upgrade_is_idempotent_when_target_constraint_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    bind = _Bind()
    inspector = _Inspector(
        constraints=[
            {
                "name": "uq_refunds_requester_key",
                "column_names": ["requested_by_user_id", "idempotency_key"],
            }
        ]
    )
    calls: list[tuple[object, ...]] = []

    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration.op,
        "drop_constraint",
        lambda *args, **kwargs: calls.append(("drop_constraint", *args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_index",
        lambda *args, **kwargs: calls.append(("drop_index", *args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "create_unique_constraint",
        lambda *args, **kwargs: calls.append(("create", *args, kwargs)),
    )

    migration.upgrade()

    assert calls == []
    assert bind.statements == []


def test_upgrade_fails_clearly_when_scoped_duplicates_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    bind = _Bind(duplicate=SimpleNamespace(duplicate_count=2))
    inspector = _Inspector(constraints=[])

    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="duplicate rows"):
        migration.upgrade()
