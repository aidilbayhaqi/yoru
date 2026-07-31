import asyncio
import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from yoru_api.core.database import create_database_engine
from yoru_api.core.settings import Settings
from yoru_api.main import create_app
from yoru_api.modules.identity.models import Partner, PartnerMembership, Role, User

pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
REDIS_URL = os.getenv("TEST_REDIS_URL")


def _integration_settings() -> Settings:
    if not DATABASE_URL or not REDIS_URL:
        pytest.skip("TEST_DATABASE_URL and TEST_REDIS_URL are required")
    return Settings(
        app_env="test",
        database_url=DATABASE_URL,
        redis_url=REDIS_URL,
        cors_allowed_origins="http://localhost:3000,http://localhost:3001",
        trusted_hosts="testserver,localhost",
        session_signing_key="integration-session-key-not-for-production",
        refresh_token_pepper="integration-refresh-pepper-not-for-production",
        auth_rate_limit_attempts=20,
    )


async def _reset_identity_data(settings: Settings) -> None:
    engine = create_database_engine(settings)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    TRUNCATE TABLE
                        audit_events,
                        refresh_token_history,
                        auth_sessions,
                        mfa_methods,
                        partner_memberships,
                        user_platform_roles,
                        user_credentials,
                        partners,
                        users
                    CASCADE
                    """
                )
            )
    finally:
        await engine.dispose()


def _register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": email,
            "full_name": "Integration Customer",
            "password": "StrongPassword!2026",
        },
    )
    assert response.status_code == 201, response.text


@pytest.mark.skipif(
    not DATABASE_URL or not REDIS_URL,
    reason="PostgreSQL and Redis integration services are not configured",
)
def test_refresh_replay_revokes_session_family() -> None:
    settings = _integration_settings()
    asyncio.run(_reset_identity_data(settings))
    app = create_app(settings)

    with TestClient(app) as client:
        _register(client, "refresh-replay@example.com")
        old_refresh = client.cookies["yoru_refresh"]
        old_csrf = client.cookies["yoru_csrf"]

        response = client.post(
            "/api/v1/auth/refresh",
            headers={
                "Origin": "http://localhost:3000",
                "X-CSRF-Token": old_csrf,
            },
        )
        assert response.status_code == 200
        assert client.cookies["yoru_refresh"] != old_refresh

        with TestClient(create_app(settings)) as replay_client:
            replay_client.cookies.set(
                "yoru_refresh",
                old_refresh,
                path="/api/v1/auth",
            )
            replay_client.cookies.set("yoru_csrf", old_csrf, path="/")
            replay = replay_client.post(
                "/api/v1/auth/refresh",
                headers={
                    "Origin": "http://localhost:3000",
                    "X-CSRF-Token": old_csrf,
                },
            )
        assert replay.status_code == 401
        assert replay.json()["code"] == "INVALID_REFRESH_TOKEN"

        current_session = client.get("/api/v1/auth/me")
        assert current_session.status_code == 401


async def _seed_partner_memberships(
    settings: Settings,
) -> tuple[UUID, UUID, UUID]:
    engine = create_database_engine(settings)
    partner_a_id = uuid4()
    partner_b_id = uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("SELECT set_config('app.is_platform_admin', 'true', true)")
            )
            user_rows = (
                await connection.execute(
                    select(User.id, User.email).where(
                        User.email.in_(
                            ["partner-a@example.com", "partner-b@example.com"]
                        )
                    )
                )
            ).all()
            users = {row.email: row.id for row in user_rows}
            role_id = await connection.scalar(
                select(Role.id).where(Role.code == "partner_owner")
            )
            assert role_id is not None
            await connection.execute(
                Partner.__table__.insert(),
                [
                    {
                        "id": partner_a_id,
                        "display_name": "Partner A",
                        "status": "verified",
                    },
                    {
                        "id": partner_b_id,
                        "display_name": "Partner B",
                        "status": "verified",
                    },
                ],
            )
            await connection.execute(
                PartnerMembership.__table__.insert(),
                [
                    {
                        "id": uuid4(),
                        "partner_id": partner_a_id,
                        "user_id": users["partner-a@example.com"],
                        "role_id": role_id,
                        "status": "active",
                    },
                    {
                        "id": uuid4(),
                        "partner_id": partner_b_id,
                        "user_id": users["partner-b@example.com"],
                        "role_id": role_id,
                        "status": "active",
                    },
                ],
            )
        return partner_a_id, partner_b_id, users["partner-a@example.com"]
    finally:
        await engine.dispose()


async def _visible_partners(settings: Settings, user_id: UUID) -> set[UUID]:
    engine = create_database_engine(settings)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    SELECT
                        set_config('app.user_id', :user_id, true),
                        set_config('app.partner_id', '', true),
                        set_config('app.is_platform_admin', 'false', true)
                    """
                ),
                {"user_id": str(user_id)},
            )
            rows = (await connection.execute(select(Partner.id))).scalars().all()
            return set(rows)
    finally:
        await engine.dispose()


@pytest.mark.skipif(
    not DATABASE_URL or not REDIS_URL,
    reason="PostgreSQL and Redis integration services are not configured",
)
def test_partner_tenant_isolation_at_api_and_rls_layers() -> None:
    settings = _integration_settings()
    asyncio.run(_reset_identity_data(settings))
    with (
        TestClient(create_app(settings)) as partner_a_client,
        TestClient(create_app(settings)) as partner_b_client,
    ):
        _register(partner_a_client, "partner-a@example.com")
        _register(partner_b_client, "partner-b@example.com")
        partner_a_id, partner_b_id, user_a_id = asyncio.run(
            _seed_partner_memberships(settings)
        )

        csrf = partner_a_client.cookies["yoru_csrf"]
        own_tenant = partner_a_client.patch(
            "/api/v1/auth/active-partner",
            headers={
                "Origin": "http://localhost:3000",
                "X-CSRF-Token": csrf,
            },
            json={"partner_id": str(partner_a_id)},
        )
        assert own_tenant.status_code == 200

        cross_tenant = partner_a_client.patch(
            "/api/v1/auth/active-partner",
            headers={
                "Origin": "http://localhost:3000",
                "X-CSRF-Token": csrf,
            },
            json={"partner_id": str(partner_b_id)},
        )
        assert cross_tenant.status_code == 403
        assert cross_tenant.json()["code"] == "TENANT_SCOPE_DENIED"

        visible = asyncio.run(_visible_partners(settings, user_a_id))
        assert visible == {partner_a_id}
