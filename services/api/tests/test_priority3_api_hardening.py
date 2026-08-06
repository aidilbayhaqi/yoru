from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.requests import Request

from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.commerce.payment_providers import enabled_payment_providers
from yoru_api.modules.finance.models import Refund
from yoru_api.modules.finance.schemas import RefundCreate
from yoru_api.modules.finance.service import FinanceService
from yoru_api.modules.identity.mobile_router import get_current_mobile_actor
from yoru_api.modules.identity.router import _refresh_cookie_path


class _MobileIdentityService:
    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def authenticate_access(self, token: str) -> object:
        self.tokens.append(token)
        return SimpleNamespace(user_id=uuid4())


def _request(*, authorization: str | None = None, cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    if cookie is not None:
        headers.append((b"cookie", cookie.encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/probe",
            "raw_path": b"/probe",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )


@pytest.mark.asyncio
async def test_mobile_actor_rejects_ambient_browser_cookie() -> None:
    service = _MobileIdentityService()
    request = _request(cookie="yoru_access=ambient-browser-cookie")

    with pytest.raises(AppError) as captured:
        await get_current_mobile_actor(request, service)  # type: ignore[arg-type]

    assert captured.value.status_code == 401
    assert captured.value.code == "AUTHENTICATION_REQUIRED"
    assert service.tokens == []


@pytest.mark.asyncio
async def test_mobile_actor_accepts_bearer_token() -> None:
    service = _MobileIdentityService()
    request = _request(authorization="Bearer native-token")

    actor = await get_current_mobile_actor(request, service)  # type: ignore[arg-type]

    assert actor.user_id is not None
    assert service.tokens == ["native-token"]


def test_refresh_cookie_path_follows_api_prefix() -> None:
    settings = Settings(
        app_env="test",
        api_v1_prefix="/internal/v2",
        database_url="postgresql+asyncpg://yoru:test@localhost:5432/yoru_test",
        session_signing_key="test-session-key-not-for-production",
        refresh_token_pepper="test-refresh-pepper-not-for-production",
    )
    assert _refresh_cookie_path(settings) == "/internal/v2/auth"


def test_payment_provider_list_is_settings_driven(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYMENT_ENABLED_PROVIDERS", "mock")
    settings = SimpleNamespace(payment_enabled_providers=("midtrans_snap",))
    assert enabled_payment_providers(settings) == frozenset({"midtrans_snap"})


def test_refund_idempotency_constraint_is_requester_scoped() -> None:
    constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in Refund.__table__.constraints
        if constraint.name
    }
    assert constraints["uq_refunds_requester_key"] == (
        "requested_by_user_id",
        "idempotency_key",
    )
    assert "uq_refunds_idempotency" not in constraints


class _ExistingRefundRepository:
    def __init__(self, existing: object) -> None:
        self.existing = existing
        self.lookup: tuple[object, str] | None = None

    async def refund_by_key(self, user_id: object, key: str) -> object:
        self.lookup = (user_id, key)
        return self.existing


@pytest.mark.asyncio
async def test_refund_idempotency_rejects_different_payload() -> None:
    user_id = uuid4()
    order_id = uuid4()
    repository = _ExistingRefundRepository(
        SimpleNamespace(order_id=order_id, amount=100_000, reason="Original reason")
    )
    service = FinanceService(repository)  # type: ignore[arg-type]
    payload = RefundCreate(order_id=uuid4(), amount=50_000, reason="Different reason")

    with pytest.raises(AppError) as captured:
        await service.create_refund(
            SimpleNamespace(user_id=user_id),
            payload,
            "same-key",
        )

    assert repository.lookup == (user_id, "same-key")
    assert captured.value.status_code == 409
    assert captured.value.code == "IDEMPOTENCY_CONFLICT"
