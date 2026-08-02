"""Add cart, checkout quote, order, inventory reservation, and payment tables.

Revision ID: 20260801_0005
Revises: 20260801_0004
Create Date: 2026-08-01
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260801_0005"
down_revision: str | None = "20260801_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("6a6098a1-d986-4b13-9c48-000000000031", "commerce.order.read"),
    ("6a6098a1-d986-4b13-9c48-000000000032", "commerce.order.manage"),
    ("6a6098a1-d986-4b13-9c48-000000000033", "platform.order.read"),
)


def _insert_permission(permission_id: str, code: str) -> None:
    op.execute(
        sa.text("INSERT INTO permissions (id, code) VALUES (:id, :code) ON CONFLICT (code) DO NOTHING")
        .bindparams(
            sa.bindparam("id", value=uuid.UUID(permission_id), type_=postgresql.UUID(as_uuid=True)),
            sa.bindparam("code", value=code, type_=sa.String(length=120)),
        )
    )


def _grant(role_code: str, permission_code: str) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT role.id, permission.id
            FROM roles role CROSS JOIN permissions permission
            WHERE role.code = :role_code AND permission.code = :permission_code
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ).bindparams(role_code=role_code, permission_code=permission_code)
    )


def _enable_customer_rls(table_name: str, customer_column: str = "customer_id") -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"""
        CREATE POLICY {table_name}_customer_all ON {table_name} FOR ALL
        USING (
            current_setting('app.is_platform_admin', true) = 'true'
            OR {customer_column} = NULLIF(current_setting('app.user_id', true), '')::uuid
        )
        WITH CHECK (
            current_setting('app.is_platform_admin', true) = 'true'
            OR {customer_column} = NULLIF(current_setting('app.user_id', true), '')::uuid
        )
    """))


def _enable_commerce_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    expression = f"""
        current_setting('app.is_platform_admin', true) = 'true'
        OR {table_name}.customer_id = NULLIF(current_setting('app.user_id', true), '')::uuid
        OR EXISTS (
            SELECT 1 FROM partner_memberships membership
            WHERE membership.partner_id = {table_name}.partner_id
              AND membership.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
              AND membership.status = 'active'
        )
    """
    op.execute(sa.text(f"CREATE POLICY {table_name}_scope_all ON {table_name} FOR ALL USING ({expression}) WITH CHECK ({expression})"))


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("currency", sa.String(3), server_default="IDR", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active','quoted','checked_out','abandoned','expired')", name="ck_carts_status"),
        sa.CheckConstraint("version >= 1", name="ck_carts_version_positive"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_carts_customer_status_updated", "carts", ["customer_id", "status", "updated_at"])
    op.create_index(
        "uq_carts_one_open_per_customer",
        "carts",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('active', 'quoted')"),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity BETWEEN 1 AND 10000", name="ck_cart_items_quantity"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
    )
    op.create_index("ix_cart_items_cart_created", "cart_items", ["cart_id", "created_at"])

    op.create_table(
        "checkout_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal_amount", sa.BigInteger(), nullable=False),
        sa.Column("discount_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("shipping_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("tax_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_amount", sa.BigInteger(), nullable=False),
        sa.Column("pricing_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active','consumed','expired','cancelled')", name="ck_checkout_quotes_status"),
        sa.CheckConstraint("subtotal_amount >= 0 AND discount_amount >= 0 AND shipping_amount >= 0 AND tax_amount >= 0 AND total_amount >= 0", name="ck_checkout_quotes_amounts"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checkout_quotes_customer_status_expiry", "checkout_quotes", ["customer_id", "status", "expires_at"])

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("state", sa.String(30), server_default="pending_payment", nullable=False),
        sa.Column("payment_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("fulfillment_status", sa.String(30), server_default="unfulfilled", nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal_amount", sa.BigInteger(), nullable=False),
        sa.Column("discount_amount", sa.BigInteger(), nullable=False),
        sa.Column("shipping_amount", sa.BigInteger(), nullable=False),
        sa.Column("tax_amount", sa.BigInteger(), nullable=False),
        sa.Column("total_amount", sa.BigInteger(), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("state IN ('pending_payment','paid','processing','shipped','delivered','completed','cancelled','expired')", name="ck_orders_state"),
        sa.CheckConstraint("payment_status IN ('pending','paid','failed','cancelled','refunded','partially_refunded')", name="ck_orders_payment_status"),
        sa.CheckConstraint("fulfillment_status IN ('unfulfilled','processing','shipped','delivered','cancelled')", name="ck_orders_fulfillment_status"),
        sa.CheckConstraint("version >= 1", name="ck_orders_version_positive"),
        sa.ForeignKeyConstraint(["quote_id"], ["checkout_quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="uq_orders_number"),
        sa.UniqueConstraint("quote_id", name="uq_orders_quote"),
    )
    op.create_index("ix_orders_customer_created", "orders", ["customer_id", "created_at"])
    op.create_index("ix_orders_partner_state_updated", "orders", ["partner_id", "state", "updated_at"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("sku", sa.String(80), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_amount", sa.BigInteger(), nullable=False),
        sa.Column("line_total", sa.BigInteger(), nullable=False),
        sa.Column("item_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity BETWEEN 1 AND 10000", name="ck_order_items_quantity"),
        sa.CheckConstraint("unit_amount >= 0 AND line_total >= 0", name="ck_order_items_amounts"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_created", "order_items", ["order_id", "created_at"])

    op.create_table(
        "inventory_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_reservations_quantity"),
        sa.CheckConstraint("status IN ('active','consumed','released','expired')", name="ck_inventory_reservations_status"),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quote_id"], ["checkout_quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_id", "product_id", name="uq_inventory_reservations_quote_product"),
    )
    op.create_index("ix_inventory_reservations_expiry", "inventory_reservations", ["status", "expires_at"])
    op.create_index("ix_inventory_reservations_order", "inventory_reservations", ["order_id", "status"])

    op.create_table(
        "payment_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_reference", sa.String(160), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("client_token", sa.String(255), nullable=True),
        sa.Column("failure_code", sa.String(120), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('requires_action','pending','succeeded','failed','cancelled','expired')", name="ck_payment_intents_status"),
        sa.CheckConstraint("amount >= 0", name="ck_payment_intents_amount"),
        sa.CheckConstraint("version >= 1", name="ck_payment_intents_version_positive"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_reference", name="uq_payment_intents_provider_ref"),
        sa.UniqueConstraint("order_id", "idempotency_key", name="uq_payment_intents_order_key"),
    )
    op.create_index("ix_payment_intents_order_created", "payment_intents", ["order_id", "created_at"])

    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_intent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_event_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["payment_intent_id"], ["payment_intents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_payment_events_provider_event"),
    )
    op.create_index("ix_payment_events_intent_created", "payment_events", ["payment_intent_id", "created_at"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route", sa.String(160), nullable=False),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actor_id", "route", "key", name="uq_idempotency_actor_route_key"),
    )
    op.create_index("ix_idempotency_records_expiry", "idempotency_records", ["expires_at"])

    for permission_id, code in PERMISSIONS:
        _insert_permission(permission_id, code)
    for role in ("partner_admin", "partner_finance", "partner_owner"):
        _grant(role, "commerce.order.read")
    for role in ("partner_admin", "partner_owner"):
        _grant(role, "commerce.order.manage")
    for code in ("commerce.order.read", "commerce.order.manage", "platform.order.read"):
        _grant("super_admin", code)
    for role in ("platform_support", "platform_finance"):
        _grant(role, "platform.order.read")

    _enable_customer_rls("carts")
    _enable_customer_rls("cart_items")
    _enable_customer_rls("checkout_quotes")
    _enable_commerce_rls("orders")
    _enable_commerce_rls("inventory_reservations")
    _enable_commerce_rls("payment_intents")
    _enable_customer_rls("idempotency_records", customer_column="actor_id")

    # Child-table policies use ownership through their parent.
    for table, parent, fk in (
        ("order_items", "orders", "order_id"),
        ("payment_events", "payment_intents", "payment_intent_id"),
    ):
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"""
            CREATE POLICY {table}_parent_scope ON {table} FOR ALL
            USING (EXISTS (
                SELECT 1 FROM {parent} parent
                WHERE parent.id = {table}.{fk}
            ))
            WITH CHECK (EXISTS (
                SELECT 1 FROM {parent} parent
                WHERE parent.id = {table}.{fk}
            ))
        """))

    op.execute(sa.text("UPDATE app_metadata SET value = '20260801_0005', updated_at = now() WHERE key = 'schema_version'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE app_metadata SET value = '20260801_0004', updated_at = now() WHERE key = 'schema_version'"))
    for table, policy in (
        ("payment_events", "payment_events_parent_scope"),
        ("order_items", "order_items_parent_scope"),
        ("idempotency_records", "idempotency_records_customer_all"),
        ("payment_intents", "payment_intents_scope_all"),
        ("inventory_reservations", "inventory_reservations_scope_all"),
        ("orders", "orders_scope_all"),
        ("checkout_quotes", "checkout_quotes_customer_all"),
        ("cart_items", "cart_items_customer_all"),
        ("carts", "carts_customer_all"),
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {table}"))
    for _, code in PERMISSIONS:
        op.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = :code)").bindparams(code=code))
        op.execute(sa.text("DELETE FROM permissions WHERE code = :code").bindparams(code=code))
    op.drop_index("ix_idempotency_records_expiry", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_payment_events_intent_created", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_index("ix_payment_intents_order_created", table_name="payment_intents")
    op.drop_table("payment_intents")
    op.drop_index("ix_inventory_reservations_order", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_expiry", table_name="inventory_reservations")
    op.drop_table("inventory_reservations")
    op.drop_index("ix_order_items_order_created", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_partner_state_updated", table_name="orders")
    op.drop_index("ix_orders_customer_created", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_checkout_quotes_customer_status_expiry", table_name="checkout_quotes")
    op.drop_table("checkout_quotes")
    op.drop_index("ix_cart_items_cart_created", table_name="cart_items")
    op.drop_table("cart_items")
    op.drop_index("uq_carts_one_open_per_customer", table_name="carts")
    op.drop_index("ix_carts_customer_status_updated", table_name="carts")
    op.drop_table("carts")
