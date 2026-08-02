"""Add booking and home-service operation tables.

Revision ID: 20260801_0006
Revises: 20260801_0005
Create Date: 2026-08-01
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260801_0006"
down_revision: str | None = "20260801_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("6a6098a1-d986-4b13-9c48-000000000041", "booking.manage"),
    ("6a6098a1-d986-4b13-9c48-000000000042", "booking.execute"),
    ("6a6098a1-d986-4b13-9c48-000000000043", "booking.tracking.write"),
    ("6a6098a1-d986-4b13-9c48-000000000044", "platform.booking.read"),
)


def _insert_permission(permission_id: str, code: str) -> None:
    op.execute(
        sa.text(
            "INSERT INTO permissions (id, code) VALUES (:id, :code) "
            "ON CONFLICT (code) DO NOTHING"
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
            FROM roles role CROSS JOIN permissions permission
            WHERE role.code = :role_code AND permission.code = :permission_code
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ).bindparams(role_code=role_code, permission_code=permission_code)
    )


def _enable_customer_rls(table_name: str, customer_column: str = "customer_id") -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_customer_all ON {table_name} FOR ALL
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR {customer_column} = NULLIF(current_setting('app.user_id', true), '')::uuid
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR {customer_column} = NULLIF(current_setting('app.user_id', true), '')::uuid
            )
            """
        )
    )


def _enable_booking_rls(table_name: str) -> None:
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
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_scope_all ON {table_name} FOR ALL
            USING ({expression})
            WITH CHECK ({expression})
            """
        )
    )


def _enable_parent_rls(table_name: str, parent_fk: str = "booking_id") -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    expression = f"""
        EXISTS (
            SELECT 1 FROM bookings booking
            WHERE booking.id = {table_name}.{parent_fk}
              AND (
                current_setting('app.is_platform_admin', true) = 'true'
                OR booking.customer_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                OR EXISTS (
                    SELECT 1 FROM partner_memberships membership
                    WHERE membership.partner_id = booking.partner_id
                      AND membership.user_id = NULLIF(
                          current_setting('app.user_id', true), ''
                      )::uuid
                      AND membership.status = 'active'
                )
              )
        )
    """
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_parent_scope ON {table_name} FOR ALL
            USING ({expression})
            WITH CHECK ({expression})
            """
        )
    )


def upgrade() -> None:
    op.create_table(
        "customer_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("recipient_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False),
        sa.Column("address_line1", sa.String(300), nullable=False),
        sa.Column("address_line2", sa.String(300), nullable=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("province", sa.String(120), nullable=False),
        sa.Column("postal_code", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_addresses_customer_default",
        "customer_addresses",
        ["customer_id", "is_default"],
    )

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("address_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), server_default="requested", nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), server_default="Asia/Jakarta", nullable=False),
        sa.Column("service_name", sa.String(180), nullable=False),
        sa.Column("service_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("address_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("customer_notes", sa.Text(), nullable=True),
        sa.Column("partner_notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_trip_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("no_show_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested','confirmed','assigned','on_the_way','arrived',"
            "'in_progress','completed','cancelled','no_show')",
            name="ck_bookings_status",
        ),
        sa.CheckConstraint("scheduled_end > scheduled_start", name="ck_bookings_schedule_order"),
        sa.CheckConstraint("amount >= 0", name="ck_bookings_amount_nonnegative"),
        sa.CheckConstraint("version >= 1", name="ck_bookings_version_positive"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id"], ["service_offerings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["address_id"], ["customer_addresses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["professional_id"], ["service_professionals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cancelled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="uq_bookings_number"),
    )
    op.create_index("ix_bookings_customer_created", "bookings", ["customer_id", "created_at"])
    op.create_index(
        "ix_bookings_partner_status_schedule",
        "bookings",
        ["partner_id", "status", "scheduled_start"],
    )
    op.create_index(
        "ix_bookings_service_schedule",
        "bookings",
        ["service_id", "scheduled_start", "scheduled_end"],
    )

    op.create_table(
        "booking_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), server_default="accepted", nullable=False),
        sa.Column("response_reason", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected','cancelled','completed')",
            name="ck_booking_assignments_status",
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_id"], ["service_professionals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_booking_assignments_booking_created",
        "booking_assignments",
        ["booking_id", "created_at"],
    )
    op.create_index(
        "ix_booking_assignments_professional_status",
        "booking_assignments",
        ["professional_id", "status"],
    )

    op.create_table(
        "booking_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("otp_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("purpose IN ('check_in','check_out')", name="ck_booking_verifications_purpose"),
        sa.CheckConstraint("attempts >= 0", name="ck_booking_verifications_attempts_nonnegative"),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 20", name="ck_booking_verifications_max_attempts"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", "purpose", name="uq_booking_verifications_purpose"),
    )

    op.create_table(
        "booking_tracking_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active','stopped','expired')", name="ck_booking_tracking_sessions_status"),
        sa.CheckConstraint("expires_at > started_at", name="ck_booking_tracking_session_expiry"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professional_id"], ["service_professionals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", name="uq_booking_tracking_sessions_booking"),
    )

    op.create_table(
        "booking_tracking_pings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("accuracy_meters", sa.Numeric(10, 2), nullable=True),
        sa.Column("heading_degrees", sa.Numeric(6, 2), nullable=True),
        sa.Column("speed_mps", sa.Numeric(10, 3), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_booking_tracking_ping_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_booking_tracking_ping_longitude"),
        sa.CheckConstraint("accuracy_meters IS NULL OR accuracy_meters >= 0", name="ck_booking_tracking_ping_accuracy"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["booking_tracking_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_id"], ["service_professionals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_booking_tracking_pings_session_recorded",
        "booking_tracking_pings",
        ["session_id", "recorded_at"],
    )

    op.create_table(
        "booking_completion_checklists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professional_id"], ["service_professionals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", name="uq_booking_completion_checklists_booking"),
    )

    for permission_id, code in PERMISSIONS:
        _insert_permission(permission_id, code)
    for role in ("partner_admin", "partner_owner"):
        for code in ("booking.manage", "booking.execute", "booking.tracking.write"):
            _grant(role, code)
    for _, code in PERMISSIONS:
        _grant("super_admin", code)
    _grant("platform_support", "platform.booking.read")

    _enable_customer_rls("customer_addresses")
    _enable_booking_rls("bookings")
    for table_name in (
        "booking_assignments",
        "booking_verifications",
        "booking_tracking_sessions",
        "booking_tracking_pings",
        "booking_completion_checklists",
    ):
        _enable_parent_rls(table_name)

    op.execute(
        sa.text(
            "UPDATE app_metadata SET value = '20260801_0006', updated_at = now() "
            "WHERE key = 'schema_version'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE app_metadata SET value = '20260801_0005', updated_at = now() "
            "WHERE key = 'schema_version'"
        )
    )
    for table_name, policy_name in (
        ("booking_completion_checklists", "booking_completion_checklists_parent_scope"),
        ("booking_tracking_pings", "booking_tracking_pings_parent_scope"),
        ("booking_tracking_sessions", "booking_tracking_sessions_parent_scope"),
        ("booking_verifications", "booking_verifications_parent_scope"),
        ("booking_assignments", "booking_assignments_parent_scope"),
        ("bookings", "bookings_scope_all"),
        ("customer_addresses", "customer_addresses_customer_all"),
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"))
    for _, code in PERMISSIONS:
        op.execute(
            sa.text(
                "DELETE FROM role_permissions WHERE permission_id IN "
                "(SELECT id FROM permissions WHERE code = :code)"
            ).bindparams(code=code)
        )
        op.execute(sa.text("DELETE FROM permissions WHERE code = :code").bindparams(code=code))

    op.drop_table("booking_completion_checklists")
    op.drop_index(
        "ix_booking_tracking_pings_session_recorded",
        table_name="booking_tracking_pings",
    )
    op.drop_table("booking_tracking_pings")
    op.drop_table("booking_tracking_sessions")
    op.drop_table("booking_verifications")
    op.drop_index(
        "ix_booking_assignments_professional_status",
        table_name="booking_assignments",
    )
    op.drop_index(
        "ix_booking_assignments_booking_created",
        table_name="booking_assignments",
    )
    op.drop_table("booking_assignments")
    op.drop_index("ix_bookings_service_schedule", table_name="bookings")
    op.drop_index("ix_bookings_partner_status_schedule", table_name="bookings")
    op.drop_index("ix_bookings_customer_created", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index(
        "ix_customer_addresses_customer_default",
        table_name="customer_addresses",
    )
    op.drop_table("customer_addresses")
