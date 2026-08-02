import uuid
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent, OutboxEvent
from yoru_api.modules.catalog.models import InventoryItem, Product
from yoru_api.modules.commerce.models import (
    Cart,
    CartItem,
    IdempotencyRecord,
    InventoryReservation,
    Order,
    OrderItem,
    PaymentEvent,
    PaymentIntent,
    Quote,
)


@dataclass(frozen=True, slots=True)
class CartLine:
    item: CartItem
    product: Product
    inventory: InventoryItem | None


@dataclass(frozen=True, slots=True)
class CartBundle:
    cart: Cart
    lines: list[CartLine]


@dataclass(frozen=True, slots=True)
class OrderBundle:
    order: Order
    items: list[OrderItem]
    payments: list[PaymentIntent]


class CommerceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_cart(self, customer_id: uuid.UUID, *, for_update: bool = False) -> Cart | None:
        statement: Select[tuple[Cart]] = select(Cart).where(
            Cart.customer_id == customer_id,
            Cart.status.in_(("active", "quoted")),
        ).order_by(Cart.updated_at.desc())
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_cart(self, cart_id: uuid.UUID, *, for_update: bool = False) -> Cart | None:
        statement: Select[tuple[Cart]] = select(Cart).where(Cart.id == cart_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_cart(self, *, customer_id: uuid.UUID, currency: str, expires_at: object) -> Cart:
        cart = Cart(customer_id=customer_id, currency=currency, expires_at=expires_at)
        self._session.add(cart)
        await self._session.flush()
        return cart

    async def list_cart_lines(self, cart_id: uuid.UUID) -> list[CartLine]:
        result = await self._session.execute(
            select(CartItem, Product, InventoryItem)
            .join(Product, Product.id == CartItem.product_id)
            .outerjoin(InventoryItem, InventoryItem.product_id == Product.id)
            .where(CartItem.cart_id == cart_id)
            .order_by(CartItem.created_at.asc(), CartItem.id.asc())
        )
        return [CartLine(item=row[0], product=row[1], inventory=row[2]) for row in result.all()]

    async def get_cart_item(self, item_id: uuid.UUID, *, for_update: bool = False) -> CartItem | None:
        statement: Select[tuple[CartItem]] = select(CartItem).where(CartItem.id == item_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_cart_item_by_product(self, cart_id: uuid.UUID, product_id: uuid.UUID) -> CartItem | None:
        return await self._session.scalar(
            select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        )

    async def add_cart_item(
        self, *, cart: Cart, product: Product, quantity: int
    ) -> CartItem:
        item = CartItem(
            cart_id=cart.id,
            customer_id=cart.customer_id,
            partner_id=product.partner_id,
            product_id=product.id,
            quantity=quantity,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def delete_cart_item(self, item: CartItem) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def get_product(self, product_id: uuid.UUID, *, for_update: bool = False) -> Product | None:
        statement: Select[tuple[Product]] = select(Product).where(Product.id == product_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_inventory(self, product_id: uuid.UUID, *, for_update: bool = False) -> InventoryItem | None:
        statement: Select[tuple[InventoryItem]] = select(InventoryItem).where(
            InventoryItem.product_id == product_id
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_quote(self, **values: object) -> Quote:
        quote = Quote(**values)
        self._session.add(quote)
        await self._session.flush()
        return quote

    async def get_quote(self, quote_id: uuid.UUID, *, for_update: bool = False) -> Quote | None:
        statement: Select[tuple[Quote]] = select(Quote).where(Quote.id == quote_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_order(self, **values: object) -> Order:
        order = Order(**values)
        self._session.add(order)
        await self._session.flush()
        return order

    async def add_order_item(self, **values: object) -> OrderItem:
        item = OrderItem(**values)
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_order(self, order_id: uuid.UUID, *, for_update: bool = False) -> Order | None:
        statement: Select[tuple[Order]] = select(Order).where(Order.id == order_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def list_orders(
        self,
        *,
        customer_id: uuid.UUID | None,
        partner_id: uuid.UUID | None,
        limit: int,
    ) -> list[Order]:
        statement = select(Order)
        if customer_id is not None:
            statement = statement.where(Order.customer_id == customer_id)
        if partner_id is not None:
            statement = statement.where(Order.partner_id == partner_id)
        result = await self._session.scalars(
            statement.order_by(Order.created_at.desc(), Order.id.desc()).limit(limit)
        )
        return list(result)

    async def list_order_items(self, order_id: uuid.UUID) -> list[OrderItem]:
        result = await self._session.scalars(
            select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.created_at.asc())
        )
        return list(result)

    async def list_payment_intents(self, order_id: uuid.UUID) -> list[PaymentIntent]:
        result = await self._session.scalars(
            select(PaymentIntent)
            .where(PaymentIntent.order_id == order_id)
            .order_by(PaymentIntent.created_at.asc())
        )
        return list(result)

    async def order_bundle(self, order: Order) -> OrderBundle:
        return OrderBundle(
            order=order,
            items=await self.list_order_items(order.id),
            payments=await self.list_payment_intents(order.id),
        )

    async def add_reservation(self, **values: object) -> InventoryReservation:
        reservation = InventoryReservation(**values)
        self._session.add(reservation)
        await self._session.flush()
        return reservation

    async def list_reservations(self, order_id: uuid.UUID, *, for_update: bool = False) -> list[InventoryReservation]:
        statement: Select[tuple[InventoryReservation]] = select(InventoryReservation).where(
            InventoryReservation.order_id == order_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.scalars(statement.order_by(InventoryReservation.id.asc()))
        return list(result)

    async def add_payment_intent(self, **values: object) -> PaymentIntent:
        intent = PaymentIntent(**values)
        self._session.add(intent)
        await self._session.flush()
        return intent

    async def get_payment_intent(self, payment_id: uuid.UUID, *, for_update: bool = False) -> PaymentIntent | None:
        statement: Select[tuple[PaymentIntent]] = select(PaymentIntent).where(PaymentIntent.id == payment_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_payment_by_reference(
        self, *, provider: str, provider_reference: str, for_update: bool = False
    ) -> PaymentIntent | None:
        statement: Select[tuple[PaymentIntent]] = select(PaymentIntent).where(
            PaymentIntent.provider == provider,
            PaymentIntent.provider_reference == provider_reference,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_payment_event(self, *, provider: str, provider_event_id: str) -> PaymentEvent | None:
        return await self._session.scalar(
            select(PaymentEvent).where(
                PaymentEvent.provider == provider,
                PaymentEvent.provider_event_id == provider_event_id,
            )
        )

    async def add_payment_event(self, **values: object) -> PaymentEvent:
        event = PaymentEvent(**values)
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_idempotency(self, *, actor_id: uuid.UUID, route: str, key: str) -> IdempotencyRecord | None:
        return await self._session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.actor_id == actor_id,
                IdempotencyRecord.route == route,
                IdempotencyRecord.key == key,
            )
        )

    async def add_idempotency(self, **values: object) -> IdempotencyRecord:
        record = IdempotencyRecord(**values)
        self._session.add(record)
        await self._session.flush()
        return record

    def add_audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        partner_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            AuditEvent(
                actor_id=actor_id,
                partner_id=partner_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                event_metadata=metadata or {},
            )
        )

    def add_outbox(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        self._session.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
            )
        )

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise

    async def rollback(self) -> None:
        await self._session.rollback()
