from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Mapping
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from yoru_api.core.problem import AppError
from yoru_api.modules.commerce.schemas import PaymentWebhookPayload


PAYMENT_TTL = timedelta(minutes=30)
_MIDTRANS_SANDBOX_URL = "https://app.sandbox.midtrans.com"
_MIDTRANS_PRODUCTION_URL = "https://app.midtrans.com"


@dataclass(frozen=True, slots=True)
class PaymentProviderResult:
    provider_reference: str
    status: str
    provider_status: str
    client_token: str | None
    actions: list[dict[str, str]]
    expires_at: datetime


def _secret_value(settings: object | None, attribute: str, env_name: str) -> str:
    configured = getattr(settings, attribute, None) if settings is not None else None
    if configured is not None:
        getter = getattr(configured, "get_secret_value", None)
        value = getter() if callable(getter) else str(configured)
        if value:
            return value
    return os.getenv(env_name, "").strip()


def _setting_value(
    settings: object | None,
    attribute: str,
    env_name: str,
    default: str,
) -> str:
    configured = getattr(settings, attribute, None) if settings is not None else None
    if configured is not None and str(configured).strip():
        return str(configured).strip()
    return os.getenv(env_name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def enabled_payment_providers() -> frozenset[str]:
    raw = os.getenv("PAYMENT_ENABLED_PROVIDERS", "mock")
    values = {item.strip().lower() for item in raw.split(",") if item.strip()}
    return frozenset(values or {"mock"})


def ensure_payment_provider_enabled(provider: str) -> None:
    if provider not in {"mock", "midtrans_snap"}:
        raise AppError(404, "PAYMENT_PROVIDER_NOT_FOUND", "Payment provider not found")
    if provider not in enabled_payment_providers():
        raise AppError(503, "PAYMENT_PROVIDER_DISABLED", "Payment provider is disabled")


def map_midtrans_status(transaction_status: str, fraud_status: str | None = None) -> str:
    status = transaction_status.strip().lower()
    fraud = (fraud_status or "").strip().lower()

    if status == "settlement":
        return "succeeded"
    if status == "capture":
        if fraud in {"", "accept"}:
            return "succeeded"
        if fraud == "challenge":
            return "pending"
        return "failed"
    if status == "pending":
        return "pending"
    if status == "deny":
        return "failed"
    if status == "cancel":
        return "cancelled"
    if status == "expire":
        return "expired"
    raise AppError(400, "PAYMENT_STATUS_UNSUPPORTED", "Payment status is unsupported")


def _safe_json(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError(
            502,
            "PAYMENT_PROVIDER_RESPONSE_INVALID",
            "Payment provider response is invalid",
        ) from exc
    if not isinstance(payload, dict):
        raise AppError(
            502,
            "PAYMENT_PROVIDER_RESPONSE_INVALID",
            "Payment provider response is invalid",
        )
    return payload


def _midtrans_error_message(payload: Mapping[str, object]) -> str:
    errors = payload.get("error_messages")
    if isinstance(errors, list):
        values = [str(item).strip() for item in errors if str(item).strip()]
        if values:
            return "; ".join(values)[:500]
    for key in ("status_message", "message", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:500]
    return "Payment provider request failed"


def _snap_base_url(settings: object | None) -> str:
    configured = _setting_value(
        settings,
        "midtrans_snap_base_url",
        "MIDTRANS_SNAP_BASE_URL",
        "",
    )
    if configured:
        return configured.rstrip("/")
    if _env_bool("MIDTRANS_IS_PRODUCTION"):
        return _MIDTRANS_PRODUCTION_URL
    return _MIDTRANS_SANDBOX_URL


def _enabled_payments() -> list[str]:
    raw = os.getenv("MIDTRANS_ENABLED_PAYMENTS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


async def create_payment(
    *,
    provider: str,
    order_id: uuid.UUID,
    order_number: str,
    amount: int,
    currency: str,
    idempotency_key: str,
    settings: object | None,
) -> PaymentProviderResult:
    ensure_payment_provider_enabled(provider)
    now = datetime.now(UTC)
    if provider == "mock":
        return PaymentProviderResult(
            provider_reference=f"mock_pi_{uuid.uuid4().hex}",
            status="pending",
            provider_status="PENDING",
            client_token=f"mock_client_{uuid.uuid4().hex}",
            actions=[],
            expires_at=now + PAYMENT_TTL,
        )

    if currency != "IDR":
        raise AppError(
            422,
            "PAYMENT_CURRENCY_UNSUPPORTED",
            "Midtrans Snap currently supports IDR checkout only",
        )

    server_key = _secret_value(settings, "midtrans_server_key", "MIDTRANS_SERVER_KEY")
    if not server_key:
        raise AppError(
            503,
            "PAYMENT_PROVIDER_NOT_CONFIGURED",
            "Midtrans server key is missing",
        )

    provider_reference = order_number[:50]
    expires_at = now + PAYMENT_TTL
    body: dict[str, object] = {
        "transaction_details": {
            "order_id": provider_reference,
            "gross_amount": amount,
        },
        "expiry": {
            "duration": int(PAYMENT_TTL.total_seconds() // 60),
            "unit": "minutes",
        },
        "page_expiry": {
            "duration": int(PAYMENT_TTL.total_seconds() // 60),
            "unit": "minutes",
        },
        "custom_field1": str(order_id),
        "custom_field2": idempotency_key[:255],
    }
    enabled_payments = _enabled_payments()
    if enabled_payments:
        body["enabled_payments"] = enabled_payments

    finish_url = os.getenv("MIDTRANS_FINISH_REDIRECT_URL", "").strip()
    error_url = os.getenv("MIDTRANS_ERROR_REDIRECT_URL", "").strip()
    callbacks: dict[str, str] = {}
    if finish_url:
        callbacks["finish"] = finish_url
    if error_url:
        callbacks["error"] = error_url
    if callbacks:
        body["callbacks"] = callbacks

    try:
        async with httpx.AsyncClient(
            base_url=_snap_base_url(settings),
            timeout=20.0,
            auth=(server_key, ""),
        ) as client:
            response = await client.post("/snap/v1/transactions", json=body)
    except httpx.TimeoutException as exc:
        raise AppError(504, "PAYMENT_PROVIDER_TIMEOUT", "Payment provider timed out") from exc
    except httpx.HTTPError as exc:
        raise AppError(
            502,
            "PAYMENT_PROVIDER_UNAVAILABLE",
            "Payment provider is unavailable",
        ) from exc

    payload = _safe_json(response)
    if response.status_code >= 400:
        raise AppError(
            502,
            "PAYMENT_PROVIDER_REJECTED",
            _midtrans_error_message(payload),
        )

    snap_token = str(payload.get("token") or "").strip()
    redirect_url = str(payload.get("redirect_url") or "").strip()
    if not snap_token or not redirect_url:
        raise AppError(
            502,
            "PAYMENT_PROVIDER_RESPONSE_INVALID",
            "Payment provider response is incomplete",
        )

    return PaymentProviderResult(
        provider_reference=provider_reference,
        status="requires_action",
        provider_status="PENDING",
        client_token=snap_token,
        actions=[
            {
                "type": "REDIRECT_CUSTOMER",
                "descriptor": "WEB_URL",
                "value": redirect_url,
            }
        ],
        expires_at=expires_at,
    )


def _decode_json(raw_body: bytes) -> dict[str, object]:
    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppError(400, "WEBHOOK_PAYLOAD_INVALID", "Webhook payload is invalid") from exc
    if not isinstance(payload, dict):
        raise AppError(400, "WEBHOOK_PAYLOAD_INVALID", "Webhook payload is invalid")
    return payload


def _header(headers: Mapping[str, str], name: str) -> str:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return ""


def _parse_mock_webhook(
    *,
    raw_body: bytes,
    headers: Mapping[str, str],
    settings: object | None,
) -> tuple[PaymentWebhookPayload, dict[str, object]]:
    secret = _secret_value(settings, "payment_webhook_secret", "PAYMENT_WEBHOOK_SECRET")
    if not secret:
        raise AppError(503, "PAYMENT_WEBHOOK_NOT_CONFIGURED", "Payment webhook is not configured")
    signature = _header(headers, "X-Yoru-Signature")
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature.lower(), expected.lower()):
        raise AppError(401, "WEBHOOK_SIGNATURE_INVALID", "Webhook signature is invalid")
    raw_payload = _decode_json(raw_body)
    try:
        payload = PaymentWebhookPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise AppError(400, "WEBHOOK_PAYLOAD_INVALID", "Webhook payload is invalid") from exc
    return payload, raw_payload


def _parse_midtrans_datetime(value: object) -> datetime:
    fallback = datetime.now(UTC)
    if not isinstance(value, str) or not value.strip():
        return fallback
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("Asia/Jakarta"))
    return parsed


def _minor_amount(value: object) -> int:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise AppError(400, "WEBHOOK_AMOUNT_INVALID", "Webhook amount is invalid") from exc
    if amount != amount.to_integral_value():
        raise AppError(400, "WEBHOOK_AMOUNT_INVALID", "Webhook amount is invalid")
    return int(amount)


def _parse_midtrans_webhook(
    *,
    raw_body: bytes,
    settings: object | None,
) -> tuple[PaymentWebhookPayload, dict[str, object]]:
    raw_payload = _decode_json(raw_body)
    server_key = _secret_value(settings, "midtrans_server_key", "MIDTRANS_SERVER_KEY")
    if not server_key:
        raise AppError(
            503,
            "PAYMENT_WEBHOOK_NOT_CONFIGURED",
            "Midtrans server key is missing",
        )

    order_id = str(raw_payload.get("order_id") or "").strip()
    status_code = str(raw_payload.get("status_code") or "").strip()
    gross_amount = str(raw_payload.get("gross_amount") or "").strip()
    signature = str(raw_payload.get("signature_key") or "").strip()
    if not order_id or not status_code or not gross_amount or not signature:
        raise AppError(400, "WEBHOOK_PAYLOAD_INVALID", "Webhook signature fields are missing")

    expected = hashlib.sha512(
        f"{order_id}{status_code}{gross_amount}{server_key}".encode("utf-8")
    ).hexdigest()
    if not hmac.compare_digest(signature.lower(), expected.lower()):
        raise AppError(401, "WEBHOOK_SIGNATURE_INVALID", "Webhook signature is invalid")

    transaction_status = str(raw_payload.get("transaction_status") or "").strip()
    fraud_status_value = raw_payload.get("fraud_status")
    fraud_status = str(fraud_status_value).strip() if fraud_status_value is not None else None
    normalized_status = map_midtrans_status(transaction_status, fraud_status)

    transaction_id = str(raw_payload.get("transaction_id") or "").strip()
    event_digest = hashlib.sha256(raw_body).hexdigest()
    event_id = f"midtrans_{event_digest}"
    if transaction_id:
        event_id = f"midtrans_{transaction_id}_{event_digest[:24]}"

    occurred_at = _parse_midtrans_datetime(
        raw_payload.get("settlement_time") or raw_payload.get("transaction_time")
    )
    failure_code = None
    if normalized_status in {"failed", "cancelled", "expired"}:
        raw_failure = raw_payload.get("status_message") or status_code
        failure_code = str(raw_failure)[:120]

    payload = PaymentWebhookPayload(
        provider_event_id=event_id,
        provider_reference=order_id,
        status=normalized_status,
        occurred_at=occurred_at,
        failure_code=failure_code,
        provider_status=transaction_status.lower(),
        amount=_minor_amount(gross_amount),
        currency=str(raw_payload.get("currency") or "IDR").upper(),
    )
    return payload, raw_payload


def parse_payment_webhook(
    *,
    provider: str,
    raw_body: bytes,
    headers: Mapping[str, str],
    settings: object | None,
) -> tuple[PaymentWebhookPayload, dict[str, object]]:
    ensure_payment_provider_enabled(provider)
    if provider == "mock":
        return _parse_mock_webhook(raw_body=raw_body, headers=headers, settings=settings)
    return _parse_midtrans_webhook(raw_body=raw_body, settings=settings)
