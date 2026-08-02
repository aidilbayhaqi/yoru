import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.core.problem import AppError
from yoru_api.modules.commerce.domain import to_minor_units
from yoru_api.modules.commerce.repository import CartBundle, CommerceRepository, OrderBundle
from yoru_api.modules.commerce.schemas import (
    AddCartItemRequest,
    CancelOrderRequest,
    CartItemResponse,
    CartResponse,
    CheckoutConfirmRequest,
    CheckoutResponse,
    CreatePaymentIntentRequest,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    PaymentIntentResponse,
    PaymentWebhookPayload,
    QuoteRequest,
    QuoteResponse,
    UpdateCartItemRequest,
)
from yoru_api.modules.commerce.service import CommerceService
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.security import constant_time_equal

router = APIRouter(tags=["Cart, checkout, order, and payment"])


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_commerce_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> CommerceService:
    return CommerceService(CommerceRepository(session))


CommerceServiceDependency = Annotated[CommerceService, Depends(get_commerce_service)]


def _validate_csrf(request: Request) -> None:
    origin = request.headers.get("Origin")
    if origin is not None and origin not in request.app.state.settings.cors_allowed_origins:
        raise AppError(403, "ORIGIN_DENIED", "Request origin is not allowed")
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not constant_time_equal(cookie_token, header_token):
        raise AppError(403, "CSRF_VALIDATION_FAILED", "CSRF validation failed")


def _require_idempotency_key(value: str | None) -> str:
    if value is None or not (8 <= len(value) <= 120):
        raise AppError(400, "IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key is required")
    return value


def _cart_response(bundle: CartBundle) -> CartResponse:
    items: list[CartItemResponse] = []
    subtotal = 0
    for line in bundle.lines:
        unit_amount = to_minor_units(line.product.unit_price)
        line_total = unit_amount * line.item.quantity
        subtotal += line_total
        items.append(
            CartItemResponse(
                id=line.item.id,
                product_id=line.product.id,
                partner_id=line.product.partner_id,
                product_name=line.product.name,
                sku=line.product.sku,
                quantity=line.item.quantity,
                unit_amount=unit_amount,
                line_total=line_total,
                currency=line.product.currency,
                available_quantity=line.inventory.available if line.inventory else None,
            )
        )
    return CartResponse(
        id=bundle.cart.id,
        status=bundle.cart.status,
        currency=bundle.cart.currency,
        version=bundle.cart.version,
        expires_at=bundle.cart.expires_at,
        items=items,
        subtotal_amount=subtotal,
    )


def _order_response(bundle: OrderBundle) -> OrderResponse:
    return OrderResponse(
        **{
            key: getattr(bundle.order, key)
            for key in OrderResponse.model_fields
            if key not in {"items", "payments"}
        },
        items=[OrderItemResponse.model_validate(item) for item in bundle.items],
        payments=[PaymentIntentResponse.model_validate(item) for item in bundle.payments],
    )


@router.get("/cart", response_model=CartResponse)
async def get_cart(actor: CurrentActor, service: CommerceServiceDependency) -> CartResponse:
    return _cart_response(await service.get_cart(actor))


@router.post("/cart/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    payload: AddCartItemRequest,
    request: Request,
    actor: CurrentActor,
    service: CommerceServiceDependency,
) -> CartResponse:
    _validate_csrf(request)
    return _cart_response(
        await service.add_cart_item(actor=actor, product_id=payload.product_id, quantity=payload.quantity)
    )


@router.patch("/cart/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    item_id: UUID,
    payload: UpdateCartItemRequest,
    request: Request,
    actor: CurrentActor,
    service: CommerceServiceDependency,
) -> CartResponse:
    _validate_csrf(request)
    return _cart_response(
        await service.update_cart_item(actor=actor, item_id=item_id, quantity=payload.quantity)
    )


@router.delete("/cart/items/{item_id}", response_model=CartResponse)
async def delete_cart_item(
    item_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: CommerceServiceDependency,
) -> CartResponse:
    _validate_csrf(request)
    return _cart_response(await service.delete_cart_item(actor=actor, item_id=item_id))


@router.post("/checkout/quote", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    payload: QuoteRequest,
    request: Request,
    actor: CurrentActor,
    service: CommerceServiceDependency,
) -> QuoteResponse:
    _validate_csrf(request)
    return QuoteResponse.model_validate(await service.create_quote(actor=actor, cart_id=payload.cart_id))


@router.post("/checkout/confirm", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def confirm_checkout(
    payload: CheckoutConfirmRequest,
    request: Request,
    actor: CurrentActor,
    service: CommerceServiceDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CheckoutResponse:
    _validate_csrf(request)
    order, payment, replay = await service.confirm_checkout(
        actor=actor,
        quote_id=payload.quote_id,
        provider=payload.payment_provider,
        idempotency_key=_require_idempotency_key(idempotency_key),
    )
    return CheckoutResponse(
        order=_order_response(order),
        payment_intent=PaymentIntentResponse.model_validate(payment),
        idempotent_replay=replay,
    )


@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    actor: CurrentActor,
    service: CommerceServiceDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> OrderListResponse:
    return OrderListResponse(data=[_order_response(item) for item in await service.list_orders(actor=actor, limit=limit)])


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    actor: CurrentActor,
    service: CommerceServiceDependency,
) -> OrderResponse:
    return _order_response(await service.get_order(actor=actor, order_id=order_id))


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    payload: CancelOrderRequest,
    request: Request,
    actor: CurrentActor,
    service: CommerceServiceDependency,
) -> OrderResponse:
    _validate_csrf(request)
    return _order_response(
        await service.cancel_order(actor=actor, order_id=order_id, reason=payload.reason)
    )


@router.post("/payments/intents", response_model=PaymentIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_intent(
    payload: CreatePaymentIntentRequest,
    request: Request,
    actor: CurrentActor,
    service: CommerceServiceDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PaymentIntentResponse:
    _validate_csrf(request)
    payment = await service.create_payment_intent(
        actor=actor,
        order_id=payload.order_id,
        provider=payload.provider,
        idempotency_key=_require_idempotency_key(idempotency_key),
    )
    return PaymentIntentResponse.model_validate(payment)


@router.post("/webhooks/payments/{provider}", response_model=PaymentIntentResponse)
async def payment_webhook(
    provider: str,
    request: Request,
    service: CommerceServiceDependency,
    signature: Annotated[str | None, Header(alias="X-Yoru-Signature")] = None,
) -> PaymentIntentResponse:
    if provider != "mock":
        raise AppError(404, "PAYMENT_PROVIDER_NOT_FOUND", "Payment provider not found")
    raw_body = await request.body()
    secret = request.app.state.settings.payment_webhook_secret.get_secret_value().encode("utf-8")
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    if signature is None or not hmac.compare_digest(signature.lower(), expected.lower()):
        raise AppError(401, "WEBHOOK_SIGNATURE_INVALID", "Webhook signature is invalid")
    try:
        raw_payload = json.loads(raw_body)
        if not isinstance(raw_payload, dict):
            raise ValueError("Webhook payload must be a JSON object")
        payload = PaymentWebhookPayload.model_validate(raw_payload)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AppError(400, "WEBHOOK_PAYLOAD_INVALID", "Webhook payload is invalid") from exc
    return PaymentIntentResponse.model_validate(
        await service.process_webhook(provider=provider, payload=payload, raw_payload=raw_payload)
    )
