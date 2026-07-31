from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.identity.models import AuthSession
from yoru_api.modules.identity.permissions import Actor
from yoru_api.modules.identity.service import IdentityService


def _settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://yoru:test@localhost:5432/yoru_test",
        session_signing_key="test-session-key-not-for-production",
        refresh_token_pepper="test-refresh-pepper-not-for-production",
    )


def _session() -> AuthSession:
    now = datetime.now(UTC)
    return AuthSession(
        id=uuid4(),
        family_id=uuid4(),
        user_id=uuid4(),
        access_token_hash="old-access",
        refresh_token_hash="old-refresh",
        access_expires_at=now + timedelta(minutes=15),
        refresh_expires_at=now + timedelta(days=30),
        last_used_at=now,
    )


def _actor(auth_session: AuthSession) -> Actor:
    return Actor(
        user_id=auth_session.user_id,
        email="customer@yoru.test",
        full_name="Customer",
        status="active",
        session_id=auth_session.id,
        active_partner_id=None,
        platform_roles=frozenset(),
        platform_permissions=frozenset(),
        memberships=(),
    )


class RefreshRepository:
    def __init__(
        self,
        *,
        current: AuthSession | None = None,
        reused: AuthSession | None = None,
    ) -> None:
        self.current = current
        self.reused = reused
        self.histories: list[tuple] = []
        self.revocations: list[tuple] = []
        self.audits: list[dict] = []
        self.commits = 0

    async def find_session_by_refresh_hash(self, token_hash, *, for_update=False):
        return self.current

    async def find_session_by_refresh_history(self, token_hash):
        return self.reused

    async def revoke_family(self, **kwargs):
        self.revocations.append(tuple(kwargs.items()))

    def add_audit(self, **kwargs):
        self.audits.append(kwargs)

    async def commit(self):
        self.commits += 1

    def add_refresh_history(self, **kwargs):
        self.histories.append(tuple(kwargs.items()))

    async def build_actor(self, auth_session):
        return _actor(auth_session)


@pytest.mark.asyncio
async def test_refresh_rotates_both_tokens_and_records_history() -> None:
    auth_session = _session()
    repository = RefreshRepository(current=auth_session)
    service = IdentityService(repository, _settings())  # type: ignore[arg-type]

    actor, tokens = await service.refresh(refresh_token="valid-refresh")

    assert actor.session_id == auth_session.id
    assert repository.histories
    assert repository.commits == 1
    assert auth_session.access_token_hash != "old-access"
    assert auth_session.refresh_token_hash != "old-refresh"
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_entire_family() -> None:
    reused_session = _session()
    repository = RefreshRepository(reused=reused_session)
    service = IdentityService(repository, _settings())  # type: ignore[arg-type]

    with pytest.raises(AppError, match="Invalid refresh token"):
        await service.refresh(refresh_token="already-consumed")

    assert repository.revocations
    assert repository.audits[0]["action"] == "identity.refresh_reuse_detected"
    assert repository.commits == 1
