from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yoru_api.modules.identity.models import AuthSession, User
from yoru_api.modules.identity.permissions import Actor
from yoru_api.modules.identity.router import get_identity_service
from yoru_api.modules.identity.security import new_token_pair
from yoru_api.modules.identity.service import AuthenticationResult


def _actor() -> Actor:
    return Actor(
        user_id=uuid4(),
        email="customer@example.com",
        full_name="Customer",
        status="active",
        session_id=uuid4(),
        active_partner_id=None,
        platform_roles=frozenset(),
        platform_permissions=frozenset(),
        memberships=(),
    )


class FakeLimiter:
    async def check(self, **kwargs) -> None:
        return None

    async def clear(self, **kwargs) -> None:
        return None

    async def close(self) -> None:
        return None


class FakeIdentityService:
    def __init__(self) -> None:
        self.actor = _actor()

    async def authenticate_access(self, access_token):
        return self.actor

    async def login(self, **kwargs):
        user = User(
            id=self.actor.user_id,
            email=self.actor.email,
            full_name=self.actor.full_name,
            status="active",
        )
        session = AuthSession(id=self.actor.session_id, user_id=self.actor.user_id)
        return AuthenticationResult(
            user=user,
            auth_session=session,
            actor=self.actor,
            tokens=new_token_pair(),
        )

    async def logout(self, *, actor):
        return None


def _client(app: FastAPI) -> TestClient:
    fake_service = FakeIdentityService()
    app.dependency_overrides[get_identity_service] = lambda: fake_service
    app.state.login_rate_limiter = FakeLimiter()
    return TestClient(app)


def test_login_sets_http_only_session_cookies(app: FastAPI) -> None:
    with _client(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "http://localhost:3000"},
            json={
                "email": "customer@example.com",
                "password": "StrongPassword!2026",
            },
        )

    assert response.status_code == 200
    cookie_headers = response.headers.get_list("set-cookie")
    assert any("yoru_access=" in value and "HttpOnly" in value for value in cookie_headers)
    assert any("yoru_refresh=" in value and "HttpOnly" in value for value in cookie_headers)
    assert any("yoru_csrf=" in value and "HttpOnly" not in value for value in cookie_headers)
    assert all("SameSite=lax" in value for value in cookie_headers)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")


def test_mutation_without_csrf_is_denied(app: FastAPI) -> None:
    with _client(app) as client:
        client.cookies.set("yoru_access", "access-token")
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://localhost:3000"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_VALIDATION_FAILED"


def test_cross_origin_login_is_denied(app: FastAPI) -> None:
    with _client(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://attacker.invalid"},
            json={
                "email": "customer@example.com",
                "password": "StrongPassword!2026",
            },
        )

    assert response.status_code == 403
    assert response.json()["code"] == "ORIGIN_DENIED"


def test_identity_routes_are_exposed_in_openapi(app: FastAPI) -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/logout-all" in paths
    assert "/api/v1/auth/active-partner" in paths
    assert "/api/v1/auth/sessions/{session_id}" in paths
