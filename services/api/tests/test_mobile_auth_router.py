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
        email="mobile.customer@example.com",
        full_name="Mobile Customer",
        status="active",
        session_id=uuid4(),
        active_partner_id=None,
        platform_roles=frozenset(),
        platform_permissions=frozenset(),
        memberships=(),
    )


class FakeLimiter:
    async def check(self, **kwargs: object) -> None:
        return None

    async def clear(self, **kwargs: object) -> None:
        return None

    async def close(self) -> None:
        return None


class FakeIdentityService:
    def __init__(self) -> None:
        self.actor = _actor()
        self.last_access_token: str | None = None

    def _authentication_result(self) -> AuthenticationResult:
        user = User(
            id=self.actor.user_id,
            email=self.actor.email,
            full_name=self.actor.full_name,
            status="active",
        )
        auth_session = AuthSession(
            id=self.actor.session_id,
            user_id=self.actor.user_id,
        )
        return AuthenticationResult(
            user=user,
            auth_session=auth_session,
            actor=self.actor,
            tokens=new_token_pair(),
        )

    async def authenticate_access(self, access_token: str | None) -> Actor:
        self.last_access_token = access_token
        return self.actor

    async def register_customer(self, **kwargs: object) -> AuthenticationResult:
        return self._authentication_result()

    async def login(self, **kwargs: object) -> AuthenticationResult:
        return self._authentication_result()

    async def refresh(self, *, refresh_token: str | None):
        assert refresh_token
        return self.actor, new_token_pair()

    async def logout(self, *, actor: Actor) -> None:
        assert actor.session_id == self.actor.session_id

    async def logout_all(self, *, actor: Actor) -> None:
        assert actor.user_id == self.actor.user_id


def _client(app: FastAPI) -> tuple[TestClient, FakeIdentityService]:
    fake_service = FakeIdentityService()
    app.dependency_overrides[get_identity_service] = lambda: fake_service
    app.state.login_rate_limiter = FakeLimiter()
    return TestClient(app), fake_service


def test_mobile_login_returns_tokens_without_cookies(app: FastAPI) -> None:
    client, _ = _client(app)
    with client:
        response = client.post(
            "/api/v1/mobile/auth/login",
            json={
                "email": "mobile.customer@example.com",
                "password": "StrongPassword!2026",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] == 900
    assert body["refresh_expires_in"] == 2_592_000
    assert body["session"]["user"]["email"] == "mobile.customer@example.com"
    assert not response.headers.get_list("set-cookie")
    assert response.headers["cache-control"] == "no-store"


def test_bearer_token_authenticates_current_actor(app: FastAPI) -> None:
    client, service = _client(app)
    with client:
        response = client.get(
            "/api/v1/mobile/auth/me",
            headers={"Authorization": "Bearer native-access-token"},
        )

    assert response.status_code == 200
    assert service.last_access_token == "native-access-token"


def test_bearer_authenticated_mutation_does_not_require_csrf(app: FastAPI) -> None:
    client, _ = _client(app)
    with client:
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer native-access-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out"}


def test_malformed_authorization_header_is_rejected(app: FastAPI) -> None:
    client, _ = _client(app)
    with client:
        response = client.get(
            "/api/v1/mobile/auth/me",
            headers={"Authorization": "Token invalid"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHORIZATION_HEADER_INVALID"


def test_mobile_auth_routes_are_exposed_in_openapi(app: FastAPI) -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/mobile/auth/register" in paths
    assert "/api/v1/mobile/auth/login" in paths
    assert "/api/v1/mobile/auth/refresh" in paths
    assert "/api/v1/mobile/auth/me" in paths
    assert "/api/v1/mobile/auth/logout" in paths
    assert "/api/v1/mobile/auth/logout-all" in paths
