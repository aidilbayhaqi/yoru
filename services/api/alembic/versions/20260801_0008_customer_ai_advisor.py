"""Add Customer AI Advisor consent, media, recommendation, feedback, and evaluation tables.

Revision ID: 20260801_0008
Revises: 20260801_0007
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260801_0008"
down_revision: str | None = "20260801_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = (
    ("6a6098a1-d986-4b13-9c48-000000000061", "platform.ai.read"),
    ("6a6098a1-d986-4b13-9c48-000000000062", "platform.ai.manage"),
    ("6a6098a1-d986-4b13-9c48-000000000063", "platform.ai.evaluate"),
)


def _seed_permission(permission_id: str, code: str) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code)
            VALUES (:permission_id, :code)
            ON CONFLICT (code) DO NOTHING
            """
        ).bindparams(
            sa.bindparam(
                "permission_id",
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
            SELECT roles.id, permissions.id
            FROM roles, permissions
            WHERE roles.code = :role_code
              AND permissions.code = :permission_code
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ).bindparams(role_code=role_code, permission_code=permission_code)
    )


def _enable_customer_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    expression = f"""
        current_setting('app.is_platform_admin', true) = 'true'
        OR COALESCE(current_setting('app.user_id', true), '') = ''
        OR {table_name}.customer_id = NULLIF(
            current_setting('app.user_id', true), ''
        )::uuid
    """
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_customer_scope ON {table_name} FOR ALL
            USING ({expression})
            WITH CHECK ({expression})
            """
        )
    )


def _enable_platform_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    expression = """
        current_setting('app.is_platform_admin', true) = 'true'
        OR COALESCE(current_setting('app.user_id', true), '') = ''
    """
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_platform_scope ON {table_name} FOR ALL
            USING ({expression})
            WITH CHECK ({expression})
            """
        )
    )


def upgrade() -> None:
    op.create_table(
        "ai_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=50), server_default="customer_ai", nullable=False),
        sa.Column("version", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("photo_processing", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("personalization", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("retention_days BETWEEN 1 AND 365", name="ck_ai_consents_retention"),
        sa.CheckConstraint("status IN ('active','revoked')", name="ck_ai_consents_status"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_consents_customer_status",
        "ai_consents",
        ["customer_id", "status", "created_at"],
    )

    op.create_table(
        "ai_advisor_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="collecting", nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("concerns", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("safety_status", sa.String(length=20), server_default="clear", nullable=False),
        sa.Column("safety_reason", sa.String(length=80), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("model_provider", sa.String(length=50), server_default="local", nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('collecting','ready','completed','blocked','failed','expired')",
            name="ck_ai_advisor_sessions_status",
        ),
        sa.CheckConstraint(
            "safety_status IN ('clear','review','blocked')",
            name="ck_ai_advisor_sessions_safety",
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consent_id"], ["ai_consents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_advisor_sessions_customer_created",
        "ai_advisor_sessions",
        ["customer_id", "created_at"],
    )
    op.create_index(
        "ix_ai_advisor_sessions_status_expires",
        "ai_advisor_sessions",
        ["status", "expires_at"],
    )

    op.create_table(
        "ai_media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="quarantine", nullable=False),
        sa.Column("scan_result", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("size_bytes BETWEEN 1 AND 10485760", name="ck_ai_media_assets_size"),
        sa.CheckConstraint(
            "status IN ('quarantine','pending_scan','clean','infected','error','deleted')",
            name="ck_ai_media_assets_status",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["ai_advisor_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key", name="uq_ai_media_assets_object_key"),
    )
    op.create_index(
        "ix_ai_media_assets_session_status",
        "ai_media_assets",
        ["session_id", "status"],
    )

    op.create_table(
        "ai_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(8, 6), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("price_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rank BETWEEN 1 AND 10", name="ck_ai_recommendations_rank"),
        sa.CheckConstraint("score BETWEEN 0 AND 1", name="ck_ai_recommendations_score"),
        sa.CheckConstraint("item_type IN ('product','service')", name="ck_ai_recommendations_type"),
        sa.CheckConstraint(
            "(item_type='product' AND product_id IS NOT NULL AND service_id IS NULL) OR "
            "(item_type='service' AND service_id IS NOT NULL AND product_id IS NULL)",
            name="ck_ai_recommendations_reference",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["ai_advisor_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id"], ["service_offerings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "rank", name="uq_ai_recommendations_session_rank"),
    )
    op.create_index(
        "ix_ai_recommendations_customer_created",
        "ai_recommendations",
        ["customer_id", "created_at"],
    )

    op.create_table(
        "ai_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("helpful", sa.Boolean(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_ai_feedback_rating"),
        sa.ForeignKeyConstraint(["session_id"], ["ai_advisor_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_ai_feedback_session"),
    )

    op.create_table(
        "ai_evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_name", sa.String(length=120), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('completed','failed')", name="ck_ai_evaluation_runs_status"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_evaluation_runs_created", "ai_evaluation_runs", ["created_at"])

    for table_name in (
        "ai_consents",
        "ai_advisor_sessions",
        "ai_media_assets",
        "ai_recommendations",
        "ai_feedback",
    ):
        _enable_customer_rls(table_name)
    _enable_platform_rls("ai_evaluation_runs")

    for permission_id, code in PERMISSIONS:
        _seed_permission(permission_id, code)
    for code in ("platform.ai.read", "platform.ai.manage", "platform.ai.evaluate"):
        _grant("super_admin", code)
    _grant("platform_support", "platform.ai.read")
    _grant("platform_verifier", "platform.ai.read")


def downgrade() -> None:
    for table_name in (
        "ai_evaluation_runs",
        "ai_feedback",
        "ai_recommendations",
        "ai_media_assets",
        "ai_advisor_sessions",
        "ai_consents",
    ):
        op.drop_table(table_name)

    permission_codes = tuple(code for _, code in PERMISSIONS)
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE code = ANY(:codes)
            )
            """
        ).bindparams(sa.bindparam("codes", value=list(permission_codes), type_=postgresql.ARRAY(sa.String())))
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(
            sa.bindparam("codes", value=list(permission_codes), type_=postgresql.ARRAY(sa.String()))
        )
    )
