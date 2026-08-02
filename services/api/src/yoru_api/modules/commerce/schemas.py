from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AddCartItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=10000)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=1, le=10000)


class CartItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    partner_id: UUID
    product_name: str
    sku: str | None
    quantity: int
    unit_amount: int
    line_total: int
    currency: str
    available_quantity: int | None


class CartResponse(BaseModel):
    id: UUID
    status: str
    currency: str
    version: int
    expires_at: datetime
    items: list[CartItemResponse]
    subtotal_amount: int


class QuoteRequest(BaseModel):
    cart_id: UUID | None = None


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cart_id: UUID
    partner_id: UUID
    status: str
    currency: str
    subtotal_amount: int
    discount_amount: int
    shipping_amount: int
    tax_amount: int
    total_amount: int
    pricing_snapshot: dict[str, object]
    expires_at: datetime
    created_at: datetime


class CheckoutConfirmRequest(BaseModel):
    quote_id: UUID
    payment_provider: Literal["mock"] = "mock"


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID | None
    product_name: str
    sku: str | None
    quantity: int
    unit_amount: int
    line_total: int
    item_snapshot: dict[str, object]


class PaymentIntentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    provider: str
    provider_reference: str | None
    amount: int
    currency: str
    status: str
    client_token: str | None
    failure_code: str | None
    expires_at: datetime
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    customer_id: UUID
    partner_id: UUID
    number: str
    state: str
    payment_status: str
    fulfillment_status: str
    currency: str
    subtotal_amount: int
    discount_amount: int
    shipping_amount: int
    tax_amount: int
    total_amount: int
    cancellation_reason: str | None
    placed_at: datetime
    paid_at: datetime | None
    cancelled_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = Field(default_factory=list)
    payments: list[PaymentIntentResponse] = Field(default_factory=list)


class OrderListResponse(BaseModel):
    data: list[OrderResponse]


class CheckoutResponse(BaseModel):
    order: OrderResponse
    payment_intent: PaymentIntentResponse
    idempotent_replay: bool = False


class CreatePaymentIntentRequest(BaseModel):
    order_id: UUID
    provider: Literal["mock"] = "mock"


class CancelOrderRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class PaymentWebhookPayload(BaseModel):
    provider_event_id: str = Field(min_length=3, max_length=160)
    provider_reference: str = Field(min_length=3, max_length=160)
    status: Literal["succeeded", "failed", "cancelled"]
    occurred_at: datetime
    failure_code: str | None = Field(default=None, max_length=120)
