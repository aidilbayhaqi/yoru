from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ShippingAddressInput(BaseModel):
    recipient_name: str = Field(min_length=2, max_length=120)
    recipient_phone: str = Field(min_length=8, max_length=32)
    address_line1: str = Field(min_length=3, max_length=240)
    address_line2: str | None = Field(default=None, max_length=240)
    district: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    province: str = Field(min_length=2, max_length=120)
    postal_code: str = Field(min_length=4, max_length=12)
    country_code: str = Field(default="ID", min_length=2, max_length=2)
    delivery_note: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class ShippingOptionResponse(BaseModel):
    code: str
    name: str
    provider: str
    amount: int
    currency: str
    estimated_days_min: int
    estimated_days_max: int
    rate_version: str

class QuoteRequest(BaseModel):
    cart_id: UUID | None = None
    fulfillment_type: Literal["pickup", "shipping"] = "pickup"
    shipping_service: Literal["regular", "express", "same_day"] | None = None
    shipping_address: ShippingAddressInput | None = None

    @model_validator(mode="after")
    def validate_fulfillment(self) -> "QuoteRequest":
        if self.fulfillment_type == "shipping":
            if self.shipping_service is None or self.shipping_address is None:
                raise ValueError("shipping_service and shipping_address are required for shipping")
        elif self.shipping_service is not None or self.shipping_address is not None:
            raise ValueError("shipping details are only valid for shipping fulfillment")
        return self


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
    shipping_address_snapshot: dict[str, object] | None = None
    shipping_method_snapshot: dict[str, object] | None = None
    expires_at: datetime
    created_at: datetime


class CheckoutConfirmRequest(BaseModel):
    quote_id: UUID
    payment_provider: Literal["mock", "midtrans_snap"] = "mock"


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


class PaymentActionResponse(BaseModel):
    type: str
    descriptor: str
    value: str

class PaymentIntentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    provider: str
    provider_reference: str | None
    provider_status: str | None = None
    actions: list[PaymentActionResponse] = Field(default_factory=list)
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
    shipping_address_snapshot: dict[str, object] | None = None
    shipping_method_snapshot: dict[str, object] | None = None
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
    provider: Literal["mock", "midtrans_snap"] = "mock"


class CancelOrderRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class PaymentWebhookPayload(BaseModel):
    provider_event_id: str = Field(min_length=3, max_length=160)
    provider_reference: str = Field(min_length=3, max_length=160)
    status: Literal["pending", "succeeded", "failed", "cancelled", "expired"]
    occurred_at: datetime
    failure_code: str | None = Field(default=None, max_length=120)
    provider_status: str | None = Field(default=None, max_length=80)
    amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
