"""Create identity, sessions, roles, memberships, and tenant RLS.

Revision ID: 20260728_0002
Revises: 20260728_0001
Create Date: 2026-07-28
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260728_0002"
down_revision: str | None = "20260728_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _role_seed_statement(
    role_id: str,
    code: str,
    scope: str,
    requires_mfa: bool,
) -> sa.TextClause:
    return sa.text(
        """
        INSERT INTO roles (id, code, scope, requires_mfa)
        VALUES (:id, :code, :scope, :requires_mfa)
        """
    ).bindparams(
        sa.bindparam(
            "id",
            value=uuid.UUID(role_id),
            type_=postgresql.UUID(as_uuid=True),
        ),
        sa.bindparam("code", value=code, type_=sa.String(length=80)),
        sa.bindparam("scope", value=scope, type_=sa.String(length=20)),
        sa.bindparam("requires_mfa", value=requires_mfa, type_=sa.Boolean()),
    )


def _permission_seed_statement(permission_id: str, code: str) -> sa.TextClause:
    return sa.text(
        "INSERT INTO permissions (id, code) VALUES (:id, :code)"
    ).bindparams(
        sa.bindparam(
            "id",
            value=uuid.UUID(permission_id),
            type_=postgresql.UUID(as_uuid=True),
        ),
        sa.bindparam("code", value=code, type_=sa.String(length=120)),
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_partners"),
    )
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("requires_mfa", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "user_credentials",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_credentials_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_credentials"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_role_permissions_role", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint(
            "role_id", "permission_id", name="pk_role_permissions"
        ),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
    )
    op.create_table(
        "user_platform_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_platform_roles_role", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_platform_roles_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_platform_roles"),
        sa.UniqueConstraint(
            "user_id", "role_id", name="uq_user_platform_roles_user_role"
        ),
    )
    op.create_table(
        "partner_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_memberships_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_memberships_role", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_memberships_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_partner_memberships"),
        sa.UniqueConstraint(
            "partner_id", "user_id", name="uq_partner_memberships_partner_user"
        ),
    )
    op.create_index(
        "ix_partner_memberships_user_status",
        "partner_memberships",
        ["user_id", "status"],
        unique=False,
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token_hash", sa.String(length=64), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_partner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=80), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("ip_prefix", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["active_partner_id"],
            ["partners.id"],
            name="fk_sessions_active_partner",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_sessions_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
    )
    op.create_index(
        "ix_auth_sessions_access_hash",
        "auth_sessions",
        ["access_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_auth_sessions_refresh_hash",
        "auth_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_auth_sessions_active_user",
        "auth_sessions",
        ["user_id", "refresh_expires_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "refresh_token_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["auth_sessions.id"],
            name="fk_refresh_history_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_token_history"),
    )
    op.create_index(
        "ix_refresh_token_history_hash",
        "refresh_token_history",
        ["token_hash"],
        unique=True,
    )
    op.create_table(
        "mfa_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method_type", sa.String(length=30), nullable=False),
        sa.Column("secret_ciphertext", sa.String(length=500), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_mfa_methods_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mfa_methods"),
        sa.UniqueConstraint(
            "user_id", "method_type", name="uq_mfa_methods_user_type"
        ),
    )

    role_rows = [
        ("3f21fd5a-20d8-41cf-a29e-da074328c002", "professional", "partner", False),
        ("3f21fd5a-20d8-41cf-a29e-da074328c003", "partner_admin", "partner", False),
        ("3f21fd5a-20d8-41cf-a29e-da074328c004", "partner_finance", "partner", True),
        ("3f21fd5a-20d8-41cf-a29e-da074328c005", "partner_owner", "partner", True),
        ("3f21fd5a-20d8-41cf-a29e-da074328c006", "platform_verifier", "platform", True),
        ("3f21fd5a-20d8-41cf-a29e-da074328c007", "platform_support", "platform", True),
        ("3f21fd5a-20d8-41cf-a29e-da074328c008", "platform_finance", "platform", True),
        ("3f21fd5a-20d8-41cf-a29e-da074328c009", "super_admin", "platform", True),
    ]
    for role_id, code, scope, requires_mfa in role_rows:
        op.execute(_role_seed_statement(role_id, code, scope, requires_mfa))

    permission_codes = [
        "account.self.read",
        "partner.profile.read",
        "partner.profile.write",
        "catalog.product.read",
        "catalog.product.write",
        "catalog.service.write",
        "professional.manage",
        "order.read",
        "booking.read",
        "finance.ledger.read",
        "finance.payout.request",
        "platform.partner.verify",
        "platform.partner.block",
        "platform.payout.approve",
        "platform.user.manage",
        "platform.audit.read",
        "platform.break_glass",
    ]
    for index, code in enumerate(permission_codes, start=1):
        permission_id = f"6a6098a1-d986-4b13-9c48-{index:012d}"
        op.execute(_permission_seed_statement(permission_id, code))

    grants = {
        "professional": ["booking.read"],
        "partner_admin": [
            "partner.profile.read",
            "partner.profile.write",
            "catalog.product.read",
            "catalog.product.write",
            "catalog.service.write",
            "professional.manage",
            "order.read",
            "booking.read",
        ],
        "partner_finance": [
            "partner.profile.read",
            "order.read",
            "booking.read",
            "finance.ledger.read",
            "finance.payout.request",
        ],
        "partner_owner": [
            "partner.profile.read",
            "partner.profile.write",
            "catalog.product.read",
            "catalog.product.write",
            "catalog.service.write",
            "professional.manage",
            "order.read",
            "booking.read",
            "finance.ledger.read",
            "finance.payout.request",
        ],
        "platform_verifier": [
            "partner.profile.read",
            "platform.partner.verify",
            "platform.audit.read",
        ],
        "platform_support": [
            "partner.profile.read",
            "order.read",
            "booking.read",
            "platform.audit.read",
        ],
        "platform_finance": [
            "partner.profile.read",
            "order.read",
            "booking.read",
            "finance.ledger.read",
            "platform.payout.approve",
            "platform.audit.read",
        ],
        "super_admin": permission_codes,
    }
    for role_code, codes in grants.items():
        for permission_code in codes:
            op.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT roles.id, permissions.id
                    FROM roles, permissions
                    WHERE roles.code = :role_code
                      AND permissions.code = :permission_code
                    """
                ).bindparams(
                    role_code=role_code,
                    permission_code=permission_code,
                )
            )

    op.execute(sa.text("ALTER TABLE partners ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE partners FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE partner_memberships ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE partner_memberships FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY partner_memberships_actor_scope
            ON partner_memberships
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY partners_actor_scope
            ON partners
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR EXISTS (
                    SELECT 1
                    FROM partner_memberships membership
                    WHERE membership.partner_id = partners.id
                      AND membership.user_id =
                          NULLIF(current_setting('app.user_id', true), '')::uuid
                      AND membership.status = 'active'
                )
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE app_metadata
            SET value = '20260728_0002', updated_at = now()
            WHERE key = 'schema_version'
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS partners_actor_scope ON partners"))
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_memberships_actor_scope ON partner_memberships"
        )
    )
    op.drop_table("mfa_methods")
    op.drop_index(
        "ix_refresh_token_history_hash", table_name="refresh_token_history"
    )
    op.drop_table("refresh_token_history")
    op.drop_index("ix_auth_sessions_active_user", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_refresh_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_access_hash", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index(
        "ix_partner_memberships_user_status", table_name="partner_memberships"
    )
    op.drop_table("partner_memberships")
    op.drop_table("user_platform_roles")
    op.drop_table("role_permissions")
    op.drop_table("user_credentials")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("partners")
    op.drop_table("users")
