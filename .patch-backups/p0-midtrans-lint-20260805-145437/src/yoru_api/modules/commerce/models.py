import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from yoru_api.core.models import Base


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (
        Index("ix_carts_customer_status_updated", "customer_id", "status", "updated_at"),
        CheckConstraint(
            "status IN ('active', 'quoted', 'checked_out', 'abandoned', 'expired')",
            name="ck_carts_status",
        ),
        CheckConstraint("version >= 1", name="ck_carts_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
        Index("ix_cart_items_cart_created", "cart_id", "created_at"),
        CheckConstraint("quantity BETWEEN 1 AND 10000", name="ck_cart_items_quantity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Quote(Base):
    __tablename__ = "checkout_quotes"
    __table_args__ = (
        Index("ix_checkout_quotes_customer_status_expiry", "customer_id", "status", "expires_at"),
        CheckConstraint(
            "status IN ('active', 'consumed', 'expired', 'cancelled')",
            name="ck_checkout_quotes_status",
        ),
        CheckConstraint("subtotal_amount >= 0", name="ck_checkout_quotes_subtotal"),
        CheckConstraint("discount_amount >= 0", name="ck_checkout_quotes_discount"),
        CheckConstraint("shipping_amount >= 0", name="ck_checkout_quotes_shipping"),
        CheckConstraint("tax_amount >= 0", name="ck_checkout_quotes_tax"),
        CheckConstraint("total_amount >= 0", name="ck_checkout_quotes_total"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    shipping_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pricing_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    shipping_address_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    shipping_method_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("number", name="uq_orders_number"),
        UniqueConstraint("quote_id", name="uq_orders_quote"),
        Index("ix_orders_customer_created", "customer_id", "created_at"),
        Index("ix_orders_partner_state_updated", "partner_id", "state", "updated_at"),
        CheckConstraint(
            "state IN ('pending_payment', 'paid', 'processing', 'shipped', 'delivered', "
            "'completed', 'cancelled', 'expired')",
            name="ck_orders_state",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'paid', 'failed', 'cancelled', 'refunded', "
            "'partially_refunded', 'expired')",
            name="ck_orders_payment_status",
        ),
        CheckConstraint(
            "fulfillment_status IN ('unfulfilled', 'processing', 'shipped', 'delivered', "
            "'cancelled')",
            name="ck_orders_fulfillment_status",
        ),
        CheckConstraint("version >= 1", name="ck_orders_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checkout_quotes.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_payment")
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    fulfillment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unfulfilled"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shipping_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shipping_address_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    shipping_method_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_created", "order_id", "created_at"),
        CheckConstraint("quantity BETWEEN 1 AND 10000", name="ck_order_items_quantity"),
        CheckConstraint("unit_amount >= 0", name="ck_order_items_unit_amount"),
        CheckConstraint("line_total >= 0", name="ck_order_items_line_total"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        UniqueConstraint("quote_id", "product_id", name="uq_inventory_reservations_quote_product"),
        Index("ix_inventory_reservations_expiry", "status", "expires_at"),
        Index("ix_inventory_reservations_order", "order_id", "status"),
        CheckConstraint("quantity > 0", name="ck_inventory_reservations_quantity"),
        CheckConstraint(
            "status IN ('active', 'consumed', 'released', 'expired')",
            name="ck_inventory_reservations_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="RESTRICT"), nullable=False
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checkout_quotes.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PaymentIntent(Base):
    __tablename__ = "payment_intents"
    __table_args__ = (
        UniqueConstraint("provider", "provider_reference", name="uq_payment_intents_provider_ref"),
        UniqueConstraint("order_id", "idempotency_key", name="uq_payment_intents_order_key"),
        Index("ix_payment_intents_order_created", "order_id", "created_at"),
        CheckConstraint(
            "status IN ('requires_action', 'pending', 'succeeded', 'failed', 'cancelled', 'expired')",
            name="ck_payment_intents_status",
        ),
        CheckConstraint("amount >= 0", name="ck_payment_intents_amount"),
        CheckConstraint("version >= 1", name="ck_payment_intents_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(160))
    provider_status: Mapped[str | None] = mapped_column(String(80))
    actions: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    client_token: Mapped[str | None] = mapped_column(String(255))
    failure_code: Mapped[str | None] = mapped_column(String(120))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_payment_events_provider_event"),
        Index("ix_payment_events_intent_created", "payment_intent_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_intent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_intents.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("actor_id", "route", "key", name="uq_idempotency_actor_route_key"),
        Index("ix_idempotency_records_expiry", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    route: Mapped[str] = mapped_column(String(160), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
