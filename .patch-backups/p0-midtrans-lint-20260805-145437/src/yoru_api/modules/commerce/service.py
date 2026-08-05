import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from yoru_api.core.problem import AppError
from yoru_api.modules.catalog.models import InventoryItem, Product
from yoru_api.modules.commerce.domain import calculate_totals, request_hash, to_minor_units
from yoru_api.modules.commerce.models import Cart, Order, PaymentIntent, Quote
from yoru_api.modules.commerce.payment_providers import (
    create_payment,
    ensure_payment_provider_enabled,
    parse_payment_webhook,
)
from yoru_api.modules.commerce.repository import CartBundle, CartLine, CommerceRepository, OrderBundle
from yoru_api.modules.commerce.schemas import PaymentWebhookPayload
from yoru_api.modules.commerce.shipping import build_shipping_quote
from yoru_api.modules.commerce.state_machine import ensure_order_transition, ensure_payment_transition
from yoru_api.modules.finance.repository import FinanceRepository
from yoru_api.modules.finance.service import FinanceService
from yoru_api.modules.identity.permissions import Actor, require_permission

CART_TTL = timedelta(days=14)
QUOTE_TTL = timedelta(minutes=15)
RESERVATION_TTL = timedelta(minutes=30)
PAYMENT_TTL = timedelta(minutes=30)
IDEMPOTENCY_TTL = timedelta(hours=24)


class CommerceService:
    def __init__(self, repository: CommerceRepository, settings: object | None = None) -> None:
        self._repository = repository
        self._settings = settings

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    async def _provider_payment(
        self,
        *,
        order: Order,
        provider: str,
        idempotency_key: str,
    ) -> PaymentIntent:
        result = await create_payment(
            provider=provider,
            order_id=order.id,
            order_number=order.number,
            amount=order.total_amount,
            currency=order.currency,
            idempotency_key=idempotency_key,
            settings=self._settings,
        )
        return await self._repository.add_payment_intent(
            order_id=order.id,
            customer_id=order.customer_id,
            partner_id=order.partner_id,
            provider=provider,
            provider_reference=result.provider_reference,
            provider_status=result.provider_status,
            actions=result.actions,
            idempotency_key=idempotency_key,
            amount=order.total_amount,
            currency=order.currency,
            status=result.status,
            client_token=result.client_token,
            expires_at=result.expires_at,
            version=1,
        )

    async def _required_product(self, product_id: uuid.UUID) -> Product:
        product = await self._repository.get_product(product_id)
        if product is None or product.status != "published":
            raise AppError(404, "CATALOG_PRODUCT_NOT_FOUND", "Catalog product not found")
        return product

    async def _required_cart(self, cart_id: uuid.UUID, actor: Actor, *, for_update: bool = False) -> Cart:
        cart = await self._repository.get_cart(cart_id, for_update=for_update)
        if cart is None or cart.customer_id != actor.user_id:
            raise AppError(404, "CART_NOT_FOUND", "Cart not found")
        return cart

    async def _required_order(self, order_id: uuid.UUID, *, for_update: bool = False) -> Order:
        order = await self._repository.get_order(order_id, for_update=for_update)
        if order is None:
            raise AppError(404, "ORDER_NOT_FOUND", "Order not found")
        return order

    async def _cart_bundle(self, cart: Cart) -> CartBundle:
        return CartBundle(cart=cart, lines=await self._repository.list_cart_lines(cart.id))

    @staticmethod
    def _ensure_cart_mutable(cart: Cart) -> None:
        if cart.status not in {"active", "quoted"}:
            raise AppError(409, "CART_STATE_CONFLICT", "Cart cannot be modified")
        if cart.expires_at <= datetime.now(UTC):
            raise AppError(409, "CART_EXPIRED", "Cart has expired")

    @staticmethod
    def _ensure_same_partner(lines: list[CartLine], product: Product | None = None) -> None:
        partner_ids = {line.product.partner_id for line in lines}
        if product is not None:
            partner_ids.add(product.partner_id)
        if len(partner_ids) > 1:
            raise AppError(
                409,
                "CROSS_PARTNER_CART_NOT_SUPPORTED",
                "This release supports one partner per cart",
            )

    @staticmethod
    def _line_amount(line: CartLine) -> int:
        return to_minor_units(line.product.unit_price)

    @staticmethod
    def _ensure_stock(product: Product, inventory: InventoryItem | None, quantity: int) -> None:
        if not product.stock_tracked:
            return
        if inventory is None or inventory.available < quantity:
            raise AppError(409, "INVENTORY_UNAVAILABLE", "Requested quantity is unavailable")

    async def get_cart(self, actor: Actor) -> CartBundle:
        cart = await self._repository.get_active_cart(actor.user_id)
        if cart is None:
            cart = await self._repository.add_cart(
                customer_id=actor.user_id,
                currency="IDR",
                expires_at=self._now() + CART_TTL,
            )
            await self._repository.commit()
        return await self._cart_bundle(cart)

    async def add_cart_item(self, *, actor: Actor, product_id: uuid.UUID, quantity: int) -> CartBundle:
        cart = await self._repository.get_active_cart(actor.user_id, for_update=True)
        if cart is None:
            cart = await self._repository.add_cart(
                customer_id=actor.user_id, currency="IDR", expires_at=self._now() + CART_TTL
            )
        self._ensure_cart_mutable(cart)
        product = await self._required_product(product_id)
        if product.currency != cart.currency:
            raise AppError(409, "CART_CURRENCY_CONFLICT", "Product currency does not match cart")
        lines = await self._repository.list_cart_lines(cart.id)
        self._ensure_same_partner(lines, product)
        inventory = await self._repository.get_inventory(product.id)
        existing = await self._repository.get_cart_item_by_product(cart.id, product.id)
        target_quantity = quantity + (existing.quantity if existing else 0)
        self._ensure_stock(product, inventory, target_quantity)
        if existing is None:
            await self._repository.add_cart_item(cart=cart, product=product, quantity=quantity)
        else:
            existing.quantity = target_quantity
        cart.status = "active"
        cart.version += 1
        cart.expires_at = self._now() + CART_TTL
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=product.partner_id,
            action="commerce.cart.item_added",
            resource_type="cart",
            resource_id=str(cart.id),
            metadata={"product_id": str(product.id), "quantity": quantity},
        )
        await self._repository.commit()
        return await self._cart_bundle(cart)

    async def update_cart_item(self, *, actor: Actor, item_id: uuid.UUID, quantity: int) -> CartBundle:
        item = await self._repository.get_cart_item(item_id, for_update=True)
        if item is None or item.customer_id != actor.user_id:
            raise AppError(404, "CART_ITEM_NOT_FOUND", "Cart item not found")
        cart = await self._required_cart(item.cart_id, actor, for_update=True)
        self._ensure_cart_mutable(cart)
        product = await self._required_product(item.product_id)
        inventory = await self._repository.get_inventory(product.id)
        self._ensure_stock(product, inventory, quantity)
        item.quantity = quantity
        cart.status = "active"
        cart.version += 1
        cart.expires_at = self._now() + CART_TTL
        await self._repository.commit()
        return await self._cart_bundle(cart)

    async def delete_cart_item(self, *, actor: Actor, item_id: uuid.UUID) -> CartBundle:
        item = await self._repository.get_cart_item(item_id, for_update=True)
        if item is None or item.customer_id != actor.user_id:
            raise AppError(404, "CART_ITEM_NOT_FOUND", "Cart item not found")
        cart = await self._required_cart(item.cart_id, actor, for_update=True)
        self._ensure_cart_mutable(cart)
        await self._repository.delete_cart_item(item)
        cart.status = "active"
        cart.version += 1
        await self._repository.commit()
        return await self._cart_bundle(cart)

    async def create_quote(
        self,
        *,
        actor: Actor,
        cart_id: uuid.UUID | None,
        fulfillment_type: str = "pickup",
        shipping_service: str | None = None,
        shipping_address: dict[str, object] | None = None,
    ) -> Quote:
        cart = (
            await self._required_cart(cart_id, actor, for_update=True)
            if cart_id is not None
            else await self._repository.get_active_cart(actor.user_id, for_update=True)
        )
        if cart is None:
            raise AppError(404, "CART_NOT_FOUND", "Cart not found")
        self._ensure_cart_mutable(cart)
        lines = await self._repository.list_cart_lines(cart.id)
        if not lines:
            raise AppError(409, "CART_EMPTY", "Cart is empty")
        self._ensure_same_partner(lines)
        snapshot_lines: list[dict[str, object]] = []
        totals_input: list[tuple[int, int]] = []
        for line in lines:
            if line.product.status != "published":
                raise AppError(409, "CATALOG_ITEM_UNAVAILABLE", "A cart item is no longer available")
            self._ensure_stock(line.product, line.inventory, line.item.quantity)
            unit_amount = self._line_amount(line)
            totals_input.append((unit_amount, line.item.quantity))
            snapshot_lines.append(
                {
                    "product_id": str(line.product.id),
                    "partner_id": str(line.product.partner_id),
                    "name": line.product.name,
                    "sku": line.product.sku,
                    "quantity": line.item.quantity,
                    "unit_amount": unit_amount,
                    "line_total": unit_amount * line.item.quantity,
                    "currency": line.product.currency,
                    "stock_tracked": line.product.stock_tracked,
                }
            )
        shipping_quote = build_shipping_quote(
            fulfillment_type=fulfillment_type,
            shipping_service=shipping_service,
            shipping_address=shipping_address,
            currency=cart.currency,
        )
        totals = calculate_totals(totals_input)
        totals["shipping_amount"] = shipping_quote.amount
        totals["total_amount"] = (
            totals["subtotal_amount"]
            - totals["discount_amount"]
            + totals["shipping_amount"]
            + totals["tax_amount"]
        )
        quote = await self._repository.add_quote(
            cart_id=cart.id,
            customer_id=actor.user_id,
            partner_id=lines[0].product.partner_id,
            status="active",
            currency=cart.currency,
            pricing_snapshot={
                "version": 1,
                "cart_version": cart.version + 1,
                "items": snapshot_lines,
                "totals": totals,
                "fulfillment_type": fulfillment_type,
                "shipping_address": shipping_quote.address_snapshot,
                "shipping_method": shipping_quote.method_snapshot,
            },
            shipping_address_snapshot=shipping_quote.address_snapshot,
            shipping_method_snapshot=shipping_quote.method_snapshot,
            expires_at=self._now() + QUOTE_TTL,
            **totals,
        )
        cart.status = "quoted"
        cart.version += 1
        self._repository.add_outbox(
            aggregate_type="quote",
            aggregate_id=str(quote.id),
            event_type="commerce.quote.created",
            payload={"quote_id": str(quote.id), "customer_id": str(actor.user_id)},
        )
        await self._repository.commit()
        return quote

    async def confirm_checkout(
        self,
        *,
        actor: Actor,
        quote_id: uuid.UUID,
        provider: str,
        idempotency_key: str,
    ) -> tuple[OrderBundle, PaymentIntent, bool]:
        ensure_payment_provider_enabled(provider)
        route = "/checkout/confirm"
        digest = request_hash({"quote_id": str(quote_id), "provider": provider})
        existing = await self._repository.get_idempotency(
            actor_id=actor.user_id, route=route, key=idempotency_key
        )
        if existing is not None:
            if existing.request_hash != digest:
                raise AppError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key payload differs")
            order = await self._required_order(uuid.UUID(str(existing.response_body["order_id"])))
            payments = await self._repository.list_payment_intents(order.id)
            if not payments:
                raise AppError(409, "PAYMENT_INTENT_MISSING", "Payment intent is missing")
            return await self._repository.order_bundle(order), payments[-1], True

        quote = await self._repository.get_quote(quote_id, for_update=True)
        if quote is None or quote.customer_id != actor.user_id:
            raise AppError(404, "QUOTE_NOT_FOUND", "Checkout quote not found")
        now = self._now()
        if quote.status != "active" or quote.expires_at <= now:
            raise AppError(409, "QUOTE_EXPIRED", "Checkout quote is no longer active")
        cart = await self._required_cart(quote.cart_id, actor, for_update=True)
        lines = await self._repository.list_cart_lines(cart.id)
        if not lines:
            raise AppError(409, "CART_EMPTY", "Cart is empty")
        snapshot_items = quote.pricing_snapshot.get("items", [])
        quoted_cart_version = int(quote.pricing_snapshot.get("cart_version", 0))
        if cart.version != quoted_cart_version or len(snapshot_items) != len(lines):
            raise AppError(409, "QUOTE_CART_MISMATCH", "Cart changed after quote creation")

        order = await self._repository.add_order(
            quote_id=quote.id,
            customer_id=actor.user_id,
            partner_id=quote.partner_id,
            number=f"YORU-{now:%Y%m%d}-{secrets.token_hex(4).upper()}",
            state="pending_payment",
            payment_status="pending",
            fulfillment_status="unfulfilled",
            currency=quote.currency,
            subtotal_amount=quote.subtotal_amount,
            discount_amount=quote.discount_amount,
            shipping_amount=quote.shipping_amount,
            tax_amount=quote.tax_amount,
            total_amount=quote.total_amount,
            shipping_address_snapshot=quote.shipping_address_snapshot,
            shipping_method_snapshot=quote.shipping_method_snapshot,
            placed_at=now,
            version=1,
        )
        for snapshot in snapshot_items:
            product_id = uuid.UUID(str(snapshot["product_id"]))
            product = await self._repository.get_product(product_id, for_update=True)
            if product is None or product.status != "published":
                raise AppError(409, "CATALOG_ITEM_UNAVAILABLE", "A quoted item is unavailable")
            quantity = int(snapshot["quantity"])
            inventory = await self._repository.get_inventory(product_id, for_update=True)
            self._ensure_stock(product, inventory, quantity)
            await self._repository.add_order_item(
                order_id=order.id,
                partner_id=order.partner_id,
                product_id=product.id,
                product_name=str(snapshot["name"]),
                sku=snapshot.get("sku"),
                quantity=quantity,
                unit_amount=int(snapshot["unit_amount"]),
                line_total=int(snapshot["line_total"]),
                item_snapshot=dict(snapshot),
            )
            if product.stock_tracked:
                if inventory is None:
                    raise AppError(409, "INVENTORY_UNAVAILABLE", "Inventory is unavailable")
                inventory.reserved += quantity
                inventory.version += 1
                await self._repository.add_reservation(
                    inventory_item_id=inventory.id,
                    product_id=product.id,
                    quote_id=quote.id,
                    order_id=order.id,
                    customer_id=actor.user_id,
                    partner_id=order.partner_id,
                    quantity=quantity,
                    status="active",
                    expires_at=now + RESERVATION_TTL,
                )
        payment = await self._provider_payment(
            order=order,
            provider=provider,
            idempotency_key=idempotency_key,
        )
        quote.status = "consumed"
        quote.consumed_at = now
        cart.status = "checked_out"
        cart.version += 1
        await self._repository.add_idempotency(
            actor_id=actor.user_id,
            route=route,
            key=idempotency_key,
            request_hash=digest,
            response_status=201,
            response_body={"order_id": str(order.id), "payment_intent_id": str(payment.id)},
            expires_at=now + IDEMPOTENCY_TTL,
        )
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=order.partner_id,
            action="commerce.checkout.confirmed",
            resource_type="order",
            resource_id=str(order.id),
            metadata={"quote_id": str(quote.id), "total_amount": order.total_amount},
        )
        self._repository.add_outbox(
            aggregate_type="order",
            aggregate_id=str(order.id),
            event_type="commerce.order.created",
            payload={"order_id": str(order.id), "customer_id": str(actor.user_id)},
        )
        try:
            await self._repository.commit()
        except IntegrityError as exc:
            raise AppError(409, "CHECKOUT_CONFLICT", "Checkout could not be completed") from exc
        return await self._repository.order_bundle(order), payment, False

    async def list_orders(self, *, actor: Actor, limit: int) -> list[OrderBundle]:
        if actor.active_partner_id is not None:
            require_permission(actor, "commerce.order.read", partner_id=actor.active_partner_id)
            orders = await self._repository.list_orders(
                customer_id=None, partner_id=actor.active_partner_id, limit=limit
            )
        else:
            orders = await self._repository.list_orders(
                customer_id=actor.user_id, partner_id=None, limit=limit
            )
        return [await self._repository.order_bundle(order) for order in orders]

    async def get_order(self, *, actor: Actor, order_id: uuid.UUID) -> OrderBundle:
        order = await self._required_order(order_id)
        if order.customer_id != actor.user_id:
            if actor.active_partner_id != order.partner_id:
                raise AppError(404, "ORDER_NOT_FOUND", "Order not found")
            require_permission(actor, "commerce.order.read", partner_id=order.partner_id)
        return await self._repository.order_bundle(order)

    async def cancel_order(self, *, actor: Actor, order_id: uuid.UUID, reason: str) -> OrderBundle:
        order = await self._required_order(order_id, for_update=True)
        is_customer = order.customer_id == actor.user_id
        if not is_customer:
            if actor.active_partner_id != order.partner_id:
                raise AppError(404, "ORDER_NOT_FOUND", "Order not found")
            require_permission(
                actor,
                "commerce.order.manage",
                partner_id=order.partner_id,
                require_partner_write=True,
            )
        ensure_order_transition(order.state, "cancelled")
        now = self._now()
        for reservation in await self._repository.list_reservations(order.id, for_update=True):
            if reservation.status != "active":
                continue
            inventory = await self._repository.get_inventory(reservation.product_id, for_update=True)
            if inventory is not None:
                inventory.reserved = max(0, inventory.reserved - reservation.quantity)
                inventory.version += 1
            reservation.status = "released"
            reservation.released_at = now
        for payment in await self._repository.list_payment_intents(order.id):
            if payment.status in {"pending", "requires_action"}:
                ensure_payment_transition(payment.status, "cancelled")
                payment.status = "cancelled"
                payment.version += 1
        order.state = "cancelled"
        order.payment_status = "cancelled"
        order.fulfillment_status = "cancelled"
        order.cancellation_reason = reason
        order.cancelled_at = now
        order.version += 1
        self._repository.add_outbox(
            aggregate_type="order",
            aggregate_id=str(order.id),
            event_type="commerce.order.cancelled",
            payload={"order_id": str(order.id), "reason": reason},
        )
        await self._repository.commit()
        return await self._repository.order_bundle(order)

    async def create_payment_intent(
        self,
        *,
        actor: Actor,
        order_id: uuid.UUID,
        provider: str,
        idempotency_key: str,
    ) -> PaymentIntent:
        ensure_payment_provider_enabled(provider)
        order = await self._required_order(order_id, for_update=True)
        if order.customer_id != actor.user_id:
            raise AppError(404, "ORDER_NOT_FOUND", "Order not found")
        if order.state != "pending_payment":
            raise AppError(409, "ORDER_PAYMENT_BLOCKED", "Order is not awaiting payment")
        existing = await self._repository.get_idempotency(
            actor_id=actor.user_id, route="/payments/intents", key=idempotency_key
        )
        digest = request_hash({"order_id": str(order_id), "provider": provider})
        if existing is not None:
            if existing.request_hash != digest:
                raise AppError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key payload differs")
            payment = await self._repository.get_payment_intent(
                uuid.UUID(str(existing.response_body["payment_intent_id"]))
            )
            if payment is None:
                raise AppError(409, "PAYMENT_INTENT_MISSING", "Payment intent is missing")
            return payment
        now = self._now()
        payment = await self._provider_payment(
            order=order,
            provider=provider,
            idempotency_key=idempotency_key,
        )
        await self._repository.add_idempotency(
            actor_id=actor.user_id,
            route="/payments/intents",
            key=idempotency_key,
            request_hash=digest,
            response_status=201,
            response_body={"payment_intent_id": str(payment.id)},
            expires_at=now + IDEMPOTENCY_TTL,
        )
        await self._repository.commit()
        return payment

    async def get_payment_intent(
        self,
        *,
        actor: Actor,
        payment_intent_id: uuid.UUID,
    ) -> PaymentIntent:
        payment = await self._repository.get_payment_intent(payment_intent_id)
        if payment is None:
            raise AppError(404, "PAYMENT_INTENT_NOT_FOUND", "Payment intent not found")
        order = await self._required_order(payment.order_id)
        if order.customer_id != actor.user_id:
            if actor.active_partner_id != order.partner_id:
                raise AppError(404, "PAYMENT_INTENT_NOT_FOUND", "Payment intent not found")
            require_permission(actor, "commerce.order.read", partner_id=order.partner_id)
        return payment

    async def process_provider_webhook(
        self,
        *,
        provider: str,
        raw_body: bytes,
        headers: dict[str, str],
    ) -> PaymentIntent:
        payload, raw_payload = parse_payment_webhook(
            provider=provider,
            raw_body=raw_body,
            headers=headers,
            settings=self._settings,
        )
        return await self.process_webhook(
            provider=provider,
            payload=payload,
            raw_payload=raw_payload,
        )

    async def process_webhook(
        self,
        *,
        provider: str,
        payload: PaymentWebhookPayload,
        raw_payload: dict[str, object],
    ) -> PaymentIntent:
        existing_event = await self._repository.get_payment_event(
            provider=provider,
            provider_event_id=payload.provider_event_id,
        )
        payment = await self._repository.get_payment_by_reference(
            provider=provider,
            provider_reference=payload.provider_reference,
            for_update=True,
        )
        if payment is None:
            raise AppError(404, "PAYMENT_INTENT_NOT_FOUND", "Payment intent not found")
        if payload.amount is not None and payload.amount != payment.amount:
            raise AppError(
                409,
                "PAYMENT_AMOUNT_MISMATCH",
                "Webhook amount does not match payment intent",
            )
        if payload.currency is not None and payload.currency != payment.currency:
            raise AppError(
                409,
                "PAYMENT_CURRENCY_MISMATCH",
                "Webhook currency does not match payment intent",
            )
        if existing_event is not None:
            return payment

        order = await self._required_order(payment.order_id, for_update=True)
        await self._repository.add_payment_event(
            payment_intent_id=payment.id,
            provider=provider,
            provider_event_id=payload.provider_event_id,
            event_type=f"payment.{payload.status}",
            verified=True,
            payload=raw_payload,
            occurred_at=payload.occurred_at,
        )
        now = self._now()
        if payload.provider_status is not None:
            payment.provider_status = payload.provider_status

        if payload.status == payment.status:
            payment.version += 1
            await self._repository.commit()
            return payment

        if payload.status == "pending":
            ensure_payment_transition(payment.status, "pending")
            payment.status = "pending"
            payment.version += 1
            event_type = "commerce.payment.pending"
        elif payload.status == "succeeded":
            ensure_payment_transition(payment.status, "succeeded")
            ensure_order_transition(order.state, "paid")
            for reservation in await self._repository.list_reservations(
                order.id,
                for_update=True,
            ):
                if reservation.status != "active":
                    continue
                inventory = await self._repository.get_inventory(
                    reservation.product_id,
                    for_update=True,
                )
                if inventory is None or inventory.reserved < reservation.quantity:
                    raise AppError(
                        409,
                        "INVENTORY_RESERVATION_CONFLICT",
                        "Inventory reservation is invalid",
                    )
                inventory.reserved -= reservation.quantity
                inventory.on_hand -= reservation.quantity
                inventory.version += 1
                reservation.status = "consumed"
                reservation.consumed_at = now
            payment.status = "succeeded"
            payment.paid_at = payload.occurred_at
            payment.version += 1
            order.state = "paid"
            order.payment_status = "paid"
            order.paid_at = payload.occurred_at
            order.version += 1
            finance_service = FinanceService(
                FinanceRepository(self._repository.session)
            )
            await finance_service.record_paid_order(
                order=order,
                payment=payment,
                occurred_at=payload.occurred_at,
            )
            event_type = "commerce.order.paid"
        else:
            target = payload.status
            ensure_payment_transition(payment.status, target)
            for reservation in await self._repository.list_reservations(
                order.id,
                for_update=True,
            ):
                if reservation.status != "active":
                    continue
                inventory = await self._repository.get_inventory(
                    reservation.product_id,
                    for_update=True,
                )
                if inventory is not None:
                    inventory.reserved = max(
                        0,
                        inventory.reserved - reservation.quantity,
                    )
                    inventory.version += 1
                reservation.status = "released"
                reservation.released_at = now
            payment.status = target
            payment.failure_code = payload.failure_code
            payment.version += 1
            if order.state == "pending_payment":
                order_target = "expired" if target == "expired" else "cancelled"
                ensure_order_transition(order.state, order_target)
                order.state = order_target
                order.payment_status = (
                    "failed"
                    if target == "failed"
                    else "expired"
                    if target == "expired"
                    else "cancelled"
                )
                order.fulfillment_status = "cancelled"
                order.cancelled_at = now
                order.cancellation_reason = f"payment_{target}"
                order.version += 1
            event_type = f"commerce.payment.{target}"

        self._repository.add_outbox(
            aggregate_type="payment_intent",
            aggregate_id=str(payment.id),
            event_type=event_type,
            payload={
                "payment_intent_id": str(payment.id),
                "order_id": str(order.id),
            },
        )
        await self._repository.commit()
        return payment
