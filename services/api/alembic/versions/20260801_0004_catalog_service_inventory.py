"""Add catalog, service offerings, inventory, professionals, and availability.

Revision ID: 20260801_0004
Revises: 20260731_0003
Create Date: 2026-08-01
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260801_0004"
down_revision: str | None = "20260731_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("6a6098a1-d986-4b13-9c48-000000000021", "catalog.product.read"),
    ("6a6098a1-d986-4b13-9c48-000000000022", "catalog.product.write"),
    ("6a6098a1-d986-4b13-9c48-000000000023", "catalog.product.submit"),
    ("6a6098a1-d986-4b13-9c48-000000000024", "catalog.service.read"),
    ("6a6098a1-d986-4b13-9c48-000000000025", "catalog.service.write"),
    ("6a6098a1-d986-4b13-9c48-000000000026", "catalog.service.submit"),
    ("6a6098a1-d986-4b13-9c48-000000000027", "catalog.inventory.write"),
    ("6a6098a1-d986-4b13-9c48-000000000028", "catalog.availability.write"),
    ("6a6098a1-d986-4b13-9c48-000000000029", "catalog.professional.write"),
    ("6a6098a1-d986-4b13-9c48-000000000030", "platform.catalog.review"),
)

PARTNER_PERMISSIONS: tuple[str, ...] = (
    "catalog.product.read",
    "catalog.product.write",
    "catalog.product.submit",
    "catalog.service.read",
    "catalog.service.write",
    "catalog.service.submit",
    "catalog.inventory.write",
    "catalog.availability.write",
    "catalog.professional.write",
)

CATEGORY_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "f4e6f4d2-6f24-40e3-8ed1-000000000001",
        "health-wellness",
        "Health & Wellness",
        "Health, wellness, and personal care offerings.",
    ),
    (
        "f4e6f4d2-6f24-40e3-8ed1-000000000002",
        "home-services",
        "Home Services",
        "Maintenance, cleaning, repair, and household services.",
    ),
    (
        "f4e6f4d2-6f24-40e3-8ed1-000000000003",
        "professional-services",
        "Professional Services",
        "Consulting and other professional services.",
    ),
    (
        "f4e6f4d2-6f24-40e3-8ed1-000000000004",
        "food-beverage",
        "Food & Beverage",
        "Food, beverage, catering, and related products.",
    ),
    (
        "f4e6f4d2-6f24-40e3-8ed1-000000000005",
        "retail-products",
        "Retail Products",
        "General physical and digital retail products.",
    ),
)


def _insert_permission(permission_id: str, code: str) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code)
            VALUES (:id, :code)
            ON CONFLICT (code) DO NOTHING
            """
        ).bindparams(
            sa.bindparam(
                "id",
                value=uuid.UUID(permission_id),
                type_=postgresql.UUID(as_uuid=True),
            ),
            sa.bindparam("code", value=code, type_=sa.String(length=120)),
        )
    )


def _grant(role_code: str, permission_code: str) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT role.id, permission.id
            FROM roles role
            CROSS JOIN permissions permission
            WHERE role.code = :role_code
              AND permission.code = :permission_code
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ).bindparams(role_code=role_code, permission_code=permission_code)
    )


def _enable_tenant_rls(table_name: str, public_expression: str | None = None) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    tenant_expression = f"""
        current_setting('app.is_platform_admin', true) = 'true'
        OR EXISTS (
            SELECT 1
            FROM partner_memberships membership
            WHERE membership.partner_id = {table_name}.partner_id
              AND membership.user_id =
                  NULLIF(current_setting('app.user_id', true), '')::uuid
              AND membership.status = 'active'
        )
    """
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_tenant_all
            ON {table_name}
            FOR ALL
            USING ({tenant_expression})
            WITH CHECK ({tenant_expression})
            """
        )
    )
    if public_expression is not None:
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_public_read
                ON {table_name}
                FOR SELECT
                USING ({public_expression})
                """
            )
        )


def upgrade() -> None:
    op.create_table(
        "catalog_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_categories"),
        sa.UniqueConstraint("code", name="uq_catalog_categories_code"),
    )
    op.create_index(
        "ix_catalog_categories_active_name",
        "catalog_categories",
        ["is_active", "name"],
        unique=False,
    )

    for category_id, code, name, description in CATEGORY_ROWS:
        op.execute(
            sa.text(
                """
                INSERT INTO catalog_categories (id, code, name, description, is_active)
                VALUES (:id, :code, :name, :description, true)
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(
                sa.bindparam(
                    "id",
                    value=uuid.UUID(category_id),
                    type_=postgresql.UUID(as_uuid=True),
                ),
                sa.bindparam("code", value=code, type_=sa.String(length=80)),
                sa.bindparam("name", value=name, type_=sa.String(length=120)),
                sa.bindparam("description", value=description, type_=sa.Text()),
            )
        )

    op.create_table(
        "catalog_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'IDR'"),
            nullable=False,
        ),
        sa.Column(
            "stock_tracked",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("unit_price >= 0", name="ck_catalog_products_price_nonnegative"),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'published', "
            "'revision_required', 'rejected', 'archived')",
            name="ck_catalog_products_status",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_catalog_products_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["catalog_categories.id"],
            name="fk_catalog_products_category",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_catalog_products_reviewer",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_products"),
        sa.UniqueConstraint(
            "partner_id", "slug", name="uq_catalog_products_partner_slug"
        ),
        sa.UniqueConstraint(
            "partner_id", "sku", name="uq_catalog_products_partner_sku"
        ),
    )
    op.create_index(
        "ix_catalog_products_public",
        "catalog_products",
        ["status", "category_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_products_partner_status",
        "catalog_products",
        ["partner_id", "status"],
        unique=False,
    )

    op.create_table(
        "catalog_product_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("alt_text", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'ready'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sort_order >= 0", name="ck_catalog_product_media_sort_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_catalog_product_media_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["catalog_products.id"],
            name="fk_catalog_product_media_product",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_product_media"),
        sa.UniqueConstraint("object_key", name="uq_catalog_product_media_object_key"),
    )
    op.create_index(
        "ix_catalog_product_media_product_order",
        "catalog_product_media",
        ["product_id", "sort_order"],
        unique=False,
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("on_hand", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reserved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reorder_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("on_hand >= 0", name="ck_inventory_items_on_hand_nonnegative"),
        sa.CheckConstraint("reserved >= 0", name="ck_inventory_items_reserved_nonnegative"),
        sa.CheckConstraint("reserved <= on_hand", name="ck_inventory_items_reserved_lte_on_hand"),
        sa.CheckConstraint(
            "reorder_level >= 0", name="ck_inventory_items_reorder_nonnegative"
        ),
        sa.CheckConstraint("version >= 1", name="ck_inventory_items_version_positive"),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_inventory_items_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["catalog_products.id"],
            name="fk_inventory_items_product",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_items"),
        sa.UniqueConstraint("product_id", name="uq_inventory_items_product"),
    )
    op.create_index(
        "ix_inventory_items_partner_updated",
        "inventory_items",
        ["partner_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "service_offerings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'IDR'"),
            nullable=False,
        ),
        sa.Column("capacity_per_slot", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "booking_notice_minutes", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "cancellation_window_minutes",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price >= 0", name="ck_service_offerings_price_nonnegative"),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 5 AND 1440",
            name="ck_service_offerings_duration_range",
        ),
        sa.CheckConstraint(
            "capacity_per_slot BETWEEN 1 AND 10000",
            name="ck_service_offerings_capacity_range",
        ),
        sa.CheckConstraint(
            "booking_notice_minutes >= 0",
            name="ck_service_offerings_booking_notice_nonnegative",
        ),
        sa.CheckConstraint(
            "cancellation_window_minutes >= 0",
            name="ck_service_offerings_cancellation_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'published', "
            "'revision_required', 'rejected', 'archived')",
            name="ck_service_offerings_status",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_service_offerings_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["catalog_categories.id"],
            name="fk_service_offerings_category",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_service_offerings_reviewer",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_offerings"),
        sa.UniqueConstraint(
            "partner_id", "slug", name="uq_service_offerings_partner_slug"
        ),
    )
    op.create_index(
        "ix_service_offerings_public",
        "service_offerings",
        ["status", "category_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_service_offerings_partner_status",
        "service_offerings",
        ["partner_id", "status"],
        unique=False,
    )

    op.create_table(
        "service_professionals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_service_professionals_partner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_professionals"),
    )
    op.create_index(
        "ix_service_professionals_partner_active",
        "service_professionals",
        ["partner_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "service_professional_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_service_professional_assignments_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["service_offerings.id"],
            name="fk_service_professional_assignments_service",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["service_professionals.id"],
            name="fk_service_professional_assignments_professional",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_professional_assignments"),
        sa.UniqueConstraint(
            "service_id",
            "professional_id",
            name="uq_service_professional_assignments_pair",
        ),
    )
    op.create_index(
        "ix_service_professional_assignments_professional",
        "service_professional_assignments",
        ["professional_id", "service_id"],
        unique=False,
    )

    op.create_table(
        "service_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'Asia/Jakarta'"),
            nullable=False,
        ),
        sa.Column(
            "slot_interval_minutes", sa.Integer(), server_default="30", nullable=False
        ),
        sa.Column("capacity_override", sa.Integer(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "weekday BETWEEN 0 AND 6", name="ck_service_availability_weekday"
        ),
        sa.CheckConstraint(
            "end_time > start_time", name="ck_service_availability_time_order"
        ),
        sa.CheckConstraint(
            "slot_interval_minutes BETWEEN 5 AND 1440",
            name="ck_service_availability_interval_range",
        ),
        sa.CheckConstraint(
            "capacity_override IS NULL OR capacity_override BETWEEN 1 AND 10000",
            name="ck_service_availability_capacity_range",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_service_availability_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["service_offerings.id"],
            name="fk_service_availability_service",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["service_professionals.id"],
            name="fk_service_availability_professional",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_availability"),
    )
    op.create_index(
        "ix_service_availability_service_weekday",
        "service_availability",
        ["service_id", "weekday", "start_time"],
        unique=False,
    )

    for permission_id, code in PERMISSIONS:
        _insert_permission(permission_id, code)
    for role_code in ("partner_admin", "partner_owner"):
        for permission_code in PARTNER_PERMISSIONS:
            _grant(role_code, permission_code)
    _grant("platform_verifier", "platform.catalog.review")
    for _, permission_code in PERMISSIONS:
        _grant("super_admin", permission_code)

    _enable_tenant_rls("catalog_products", "catalog_products.status = 'published'")
    _enable_tenant_rls(
        "catalog_product_media",
        """
        EXISTS (
            SELECT 1
            FROM catalog_products product
            WHERE product.id = catalog_product_media.product_id
              AND product.status = 'published'
        )
        """,
    )
    _enable_tenant_rls(
        "inventory_items",
        """
        EXISTS (
            SELECT 1
            FROM catalog_products product
            WHERE product.id = inventory_items.product_id
              AND product.status = 'published'
        )
        """,
    )
    _enable_tenant_rls("service_offerings", "service_offerings.status = 'published'")
    _enable_tenant_rls(
        "service_professionals",
        """
        service_professionals.is_active = true
        AND EXISTS (
            SELECT 1
            FROM service_professional_assignments assignment
            JOIN service_offerings service ON service.id = assignment.service_id
            WHERE assignment.professional_id = service_professionals.id
              AND service.status = 'published'
        )
        """,
    )
    _enable_tenant_rls(
        "service_professional_assignments",
        """
        EXISTS (
            SELECT 1
            FROM service_offerings service
            WHERE service.id = service_professional_assignments.service_id
              AND service.status = 'published'
        )
        """,
    )
    _enable_tenant_rls(
        "service_availability",
        """
        service_availability.is_active = true
        AND EXISTS (
            SELECT 1
            FROM service_offerings service
            WHERE service.id = service_availability.service_id
              AND service.status = 'published'
        )
        """,
    )

    op.execute(
        sa.text(
            """
            UPDATE app_metadata
            SET value = '20260801_0004', updated_at = now()
            WHERE key = 'schema_version'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE app_metadata
            SET value = '20260731_0003', updated_at = now()
            WHERE key = 'schema_version'
            """
        )
    )

    for table_name in (
        "service_availability",
        "service_professional_assignments",
        "service_professionals",
        "service_offerings",
        "inventory_items",
        "catalog_product_media",
        "catalog_products",
    ):
        op.execute(
            sa.text(f"DROP POLICY IF EXISTS {table_name}_public_read ON {table_name}")
        )
        op.execute(
            sa.text(f"DROP POLICY IF EXISTS {table_name}_tenant_all ON {table_name}")
        )

    for _, permission_code in PERMISSIONS:
        op.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE code = :permission_code
                )
                """
            ).bindparams(permission_code=permission_code)
        )
        op.execute(
            sa.text("DELETE FROM permissions WHERE code = :permission_code").bindparams(
                permission_code=permission_code
            )
        )

    op.drop_index(
        "ix_service_availability_service_weekday", table_name="service_availability"
    )
    op.drop_table("service_availability")
    op.drop_index(
        "ix_service_professional_assignments_professional",
        table_name="service_professional_assignments",
    )
    op.drop_table("service_professional_assignments")
    op.drop_index(
        "ix_service_professionals_partner_active", table_name="service_professionals"
    )
    op.drop_table("service_professionals")
    op.drop_index(
        "ix_service_offerings_partner_status", table_name="service_offerings"
    )
    op.drop_index("ix_service_offerings_public", table_name="service_offerings")
    op.drop_table("service_offerings")
    op.drop_index("ix_inventory_items_partner_updated", table_name="inventory_items")
    op.drop_table("inventory_items")
    op.drop_index(
        "ix_catalog_product_media_product_order", table_name="catalog_product_media"
    )
    op.drop_table("catalog_product_media")
    op.drop_index("ix_catalog_products_partner_status", table_name="catalog_products")
    op.drop_index("ix_catalog_products_public", table_name="catalog_products")
    op.drop_table("catalog_products")
    op.drop_index(
        "ix_catalog_categories_active_name", table_name="catalog_categories"
    )
    op.drop_table("catalog_categories")
