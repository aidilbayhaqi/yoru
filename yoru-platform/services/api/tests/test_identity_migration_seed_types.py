from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import ModuleType

from sqlalchemy.dialects.postgresql import asyncpg


def _load_identity_migration() -> ModuleType:
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260728_0002_identity_authorization.py"
    )
    spec = importlib.util.spec_from_file_location(
        "identity_authorization_migration",
        migration_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_role_seed_binds_id_as_postgresql_uuid() -> None:
    migration = _load_identity_migration()

    statement = migration._role_seed_statement(
        "3f21fd5a-20d8-41cf-a29e-da074328c002",
        "professional",
        "partner",
        False,
    )
    compiled = statement.compile(dialect=asyncpg.dialect())

    assert "::UUID" in compiled.string
    assert isinstance(compiled.params["id"], uuid.UUID)


def test_permission_seed_binds_id_as_postgresql_uuid() -> None:
    migration = _load_identity_migration()

    statement = migration._permission_seed_statement(
        "6a6098a1-d986-4b13-9c48-000000000001",
        "account.self.read",
    )
    compiled = statement.compile(dialect=asyncpg.dialect())

    assert "::UUID" in compiled.string
    assert isinstance(compiled.params["id"], uuid.UUID)
