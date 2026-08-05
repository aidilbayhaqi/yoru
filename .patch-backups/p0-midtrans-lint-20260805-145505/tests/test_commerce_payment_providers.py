import asyncio
import hashlib
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from yoru_api.core.problem import AppError
from yoru_api.modules.commerce import payment_providers
from yoru_api.modules.commerce.payment_providers import (
    create_payment,
    map_midtrans_status,
    parse_payment_webhook,
)


def _signed_payload(
    *,
    server_key: str,
    transaction_status: str = "settlement",
    fraud_status: str = "accept",
) -> bytes:
    payload: dict[str, object] = {
        "transaction_time": "2026-08-05 14:00:00",
        "transaction_status": transaction_status,
        "transaction_id": "midtrans-trx-1",
        "status_message": "midtrans payment notification",
        "status_code": "200",
        "payment_type": "qris",
        "order_id": "YORU-20260805-TEST",
        "gross_amount": "100000.00",
        "fraud_status": fraud_status,
        "currency": "IDR",
    }
    raw_signature = (
        f"{payload['order_id']}{payload['status_code']}{payload['gross_amount']}{server_key}"
    )
    payload["signature_key"] = hashlib.sha512(raw_signature.encode("utf-8")).hexdigest()
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def test_midtrans_status_mapping() -> None:
    assert map_midtrans_status("settlement") == "succeeded"
    assert map_midtrans_status("capture", "accept") == "succeeded"
    assert map_midtrans_status("capture", "challenge") == "pending"
    assert map_midtrans_status("pending") == "pending"
    assert map_midtrans_status("deny") == "failed"
    assert map_midtrans_status("cancel") == "cancelled"
    assert map_midtrans_status("expire") == "expired"


def test_unknown_midtrans_status_is_rejected() -> None:
    with pytest.raises(AppError):
        map_midtrans_status("mystery")


def test_create_midtrans_snap_returns_redirect_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 201

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "token": "snap-token-test",
                "redirect_url": "https://app.sandbox.midtrans.com/snap/v4/redirection/test",
            }

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["auth"] == ("SB-Mid-server-test", "")
            assert kwargs["base_url"] == "https://app.sandbox.midtrans.com"

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, path: str, *, json: dict[str, object]) -> FakeResponse:
            assert path == "/snap/v1/transactions"
            details = json["transaction_details"]
            assert isinstance(details, dict)
            assert details["gross_amount"] == 100_000
            assert json["expiry"] == {"duration": 30, "unit": "minutes"}
            assert json["page_expiry"] == {"duration": 30, "unit": "minutes"}
            return FakeResponse()

    monkeypatch.setenv("PAYMENT_ENABLED_PROVIDERS", "midtrans_snap")
    monkeypatch.setenv("MIDTRANS_SERVER_KEY", "SB-Mid-server-test")
    monkeypatch.setenv("MIDTRANS_IS_PRODUCTION", "false")
    monkeypatch.setattr(payment_providers.httpx, "AsyncClient", FakeClient)

    result = asyncio.run(
        create_payment(
            provider="midtrans_snap",
            order_id=uuid.uuid4(),
            order_number="YORU-20260805-TEST",
            amount=100_000,
            currency="IDR",
            idempotency_key="checkout-test-key",
            settings=None,
        )
    )

    assert result.provider_reference == "YORU-20260805-TEST"
    assert result.status == "requires_action"
    assert result.provider_status == "PENDING"
    assert result.client_token == "snap-token-test"
    assert result.actions[0]["descriptor"] == "WEB_URL"


def test_midtrans_webhook_rejects_invalid_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYMENT_ENABLED_PROVIDERS", "mock,midtrans_snap")
    monkeypatch.setenv("MIDTRANS_SERVER_KEY", "server-key")
    raw = _signed_payload(server_key="wrong-key")

    with pytest.raises(AppError):
        parse_payment_webhook(
            provider="midtrans_snap",
            raw_body=raw,
            headers={},
            settings=None,
        )


def test_midtrans_webhook_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYMENT_ENABLED_PROVIDERS", "mock,midtrans_snap")
    monkeypatch.setenv("MIDTRANS_SERVER_KEY", "server-key")
    raw = _signed_payload(server_key="server-key")

    payload, raw_payload = parse_payment_webhook(
        provider="midtrans_snap",
        raw_body=raw,
        headers={},
        settings=None,
    )

    assert payload.provider_reference == "YORU-20260805-TEST"
    assert payload.status == "succeeded"
    assert payload.provider_status == "settlement"
    assert payload.amount == 100_000
    assert payload.currency == "IDR"
    assert payload.occurred_at == datetime(
        2026,
        8,
        5,
        14,
        0,
        tzinfo=ZoneInfo("Asia/Jakarta"),
    )
    assert raw_payload["payment_type"] == "qris"


def test_midtrans_challenge_remains_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYMENT_ENABLED_PROVIDERS", "midtrans_snap")
    monkeypatch.setenv("MIDTRANS_SERVER_KEY", "server-key")
    raw = _signed_payload(
        server_key="server-key",
        transaction_status="capture",
        fraud_status="challenge",
    )

    payload, _ = parse_payment_webhook(
        provider="midtrans_snap",
        raw_body=raw,
        headers={},
        settings=None,
    )

    assert payload.status == "pending"
