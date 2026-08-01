"""Add partner onboarding, verification, document, and service-area workflow.

Revision ID: 20260731_0003
Revises: 20260728_0002
Create Date: 2026-07-31
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260731_0003"
down_revision: str | None = "20260728_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _permission_seed_statement(permission_id: str, code: str) -> sa.TextClause:
    return sa.text(
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


def upgrade() -> None:
    op.add_column("partners", sa.Column("legal_name", sa.String(length=200), nullable=True))
    op.add_column("partners", sa.Column("partner_type", sa.String(length=40), nullable=True))
    op.add_column("partners", sa.Column("contact_email", sa.String(length=320), nullable=True))
    op.add_column("partners", sa.Column("contact_phone", sa.String(length=40), nullable=True))
    op.add_column("partners", sa.Column("address_line", sa.String(length=300), nullable=True))
    op.add_column("partners", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("partners", sa.Column("province", sa.String(length=120), nullable=True))
    op.add_column("partners", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column("partners", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "partners",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "partners",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "partners",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "partners",
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("partners", sa.Column("review_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_partners_created_by_user",
        "partners",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_partners_reviewed_by_user",
        "partners",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_partners_status_updated",
        "partners",
        ["status", "updated_at"],
        unique=False,
    )

    op.create_table(
        "partner_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "checklist",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_partner_verifications_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name="fk_partner_verifications_reviewer",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_partner_verifications"),
        sa.UniqueConstraint("partner_id", name="uq_partner_verifications_partner"),
    )
    op.create_index(
        "ix_partner_verifications_status_updated",
        "partner_verifications",
        ["status", "updated_at"],
        unique=False,
    )

    op.create_table(
        "partner_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=60), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("scan_status", sa.String(length=30), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_detail", sa.String(length=300), nullable=True),
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
        sa.CheckConstraint("size_bytes >= 0", name="ck_partner_documents_size_nonnegative"),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_partner_documents_partner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name="fk_partner_documents_uploader",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_partner_documents"),
        sa.UniqueConstraint("object_key", name="uq_partner_documents_object_key"),
    )
    op.create_index(
        "ix_partner_documents_partner_kind",
        "partner_documents",
        ["partner_id", "kind"],
        unique=False,
    )
    op.create_index(
        "ix_partner_documents_scan_status",
        "partner_documents",
        ["scan_status", "created_at"],
        unique=False,
    )

    op.create_table(
        "service_areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("area_type", sa.String(length=30), nullable=False),
        sa.Column("center_latitude", sa.Float(), nullable=True),
        sa.Column("center_longitude", sa.Float(), nullable=True),
        sa.Column("radius_km", sa.Float(), nullable=True),
        sa.Column(
            "postal_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "area_type IN ('radius', 'postal_codes')",
            name="ck_service_areas_type",
        ),
        sa.CheckConstraint(
            "radius_km IS NULL OR radius_km > 0",
            name="ck_service_areas_radius_positive",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name="fk_service_areas_partner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_areas"),
    )
    op.create_index(
        "ix_service_areas_partner_status",
        "service_areas",
        ["partner_id", "status"],
        unique=False,
    )

    permission_rows = [
        ("6a6098a1-d986-4b13-9c48-000000000018", "partner.document.write"),
        ("6a6098a1-d986-4b13-9c48-000000000019", "partner.service_area.write"),
        ("6a6098a1-d986-4b13-9c48-000000000020", "platform.partner.document.scan"),
    ]
    for permission_id, code in permission_rows:
        op.execute(_permission_seed_statement(permission_id, code))

    for role_code in ("partner_admin", "partner_owner"):
        _grant(role_code, "partner.document.write")
        _grant(role_code, "partner.service_area.write")
    _grant("platform_verifier", "platform.partner.document.scan")
    for permission_code in (
        "partner.document.write",
        "partner.service_area.write",
        "platform.partner.document.scan",
    ):
        _grant("super_admin", permission_code)

    op.execute(sa.text("DROP POLICY IF EXISTS partners_actor_scope ON partners"))
    op.execute(
        sa.text(
            """
            CREATE POLICY partners_actor_scope
            ON partners
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR created_by_user_id =
                    NULLIF(current_setting('app.user_id', true), '')::uuid
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
                OR (
                    created_by_user_id =
                        NULLIF(current_setting('app.user_id', true), '')::uuid
                    AND id = NULLIF(
                        current_setting('app.partner_application_id', true),
                        ''
                    )::uuid
                )
                OR EXISTS (
                    SELECT 1
                    FROM partner_memberships membership
                    WHERE membership.partner_id = partners.id
                      AND membership.user_id =
                          NULLIF(current_setting('app.user_id', true), '')::uuid
                      AND membership.status = 'active'
                )
            )
            """
        )
    )

    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_memberships_actor_scope ON partner_memberships"
        )
    )
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
                OR (
                    user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                    AND partner_id = NULLIF(
                        current_setting('app.partner_application_id', true),
                        ''
                    )::uuid
                )
            )
            """
        )
    )

    tenant_policy = """
        current_setting('app.is_platform_admin', true) = 'true'
        OR EXISTS (
            SELECT 1
            FROM partner_memberships membership
            WHERE membership.partner_id = {table}.partner_id
              AND membership.user_id =
                  NULLIF(current_setting('app.user_id', true), '')::uuid
              AND membership.status = 'active'
        )
    """
    for table_name in ("partner_documents", "service_areas"):
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
        expression = tenant_policy.format(table=table_name)
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_actor_scope
                ON {table_name}
                USING ({expression})
                WITH CHECK ({expression})
                """
            )
        )

    op.execute(sa.text("ALTER TABLE partner_verifications ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE partner_verifications FORCE ROW LEVEL SECURITY"))
    verification_select = tenant_policy.format(table="partner_verifications")
    op.execute(
        sa.text(
            f"""
            CREATE POLICY partner_verifications_actor_read
            ON partner_verifications
            FOR SELECT
            USING ({verification_select})
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY partner_verifications_platform_write
            ON partner_verifications
            FOR ALL
            USING (current_setting('app.is_platform_admin', true) = 'true')
            WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY partner_verifications_owner_insert
            ON partner_verifications
            FOR INSERT
            WITH CHECK (
                partner_id = NULLIF(
                    current_setting('app.partner_application_id', true),
                    ''
                )::uuid
                AND EXISTS (
                    SELECT 1
                    FROM partners
                    WHERE partners.id = partner_verifications.partner_id
                      AND partners.created_by_user_id =
                          NULLIF(current_setting('app.user_id', true), '')::uuid
                )
            )
            """
        )
    )
    verification_tenant = tenant_policy.format(table="partner_verifications")
    op.execute(
        sa.text(
            f"""
            CREATE POLICY partner_verifications_tenant_update
            ON partner_verifications
            FOR UPDATE
            USING ({verification_tenant})
            WITH CHECK ({verification_tenant})
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE app_metadata
            SET value = '20260731_0003', updated_at = now()
            WHERE key = 'schema_version'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE app_metadata
            SET value = '20260728_0002', updated_at = now()
            WHERE key = 'schema_version'
            """
        )
    )

    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_verifications_tenant_update "
            "ON partner_verifications"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_verifications_owner_insert "
            "ON partner_verifications"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_verifications_platform_write "
            "ON partner_verifications"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_verifications_actor_read "
            "ON partner_verifications"
        )
    )
    op.execute(
        sa.text("DROP POLICY IF EXISTS service_areas_actor_scope ON service_areas")
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_documents_actor_scope ON partner_documents"
        )
    )

    op.execute(sa.text("DROP POLICY IF EXISTS partners_actor_scope ON partners"))
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS partner_memberships_actor_scope ON partner_memberships"
        )
    )
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
            DELETE FROM permissions
            WHERE code IN (
                'partner.document.write',
                'partner.service_area.write',
                'platform.partner.document.scan'
            )
            """
        )
    )

    op.drop_index("ix_service_areas_partner_status", table_name="service_areas")
    op.drop_table("service_areas")
    op.drop_index("ix_partner_documents_scan_status", table_name="partner_documents")
    op.drop_index("ix_partner_documents_partner_kind", table_name="partner_documents")
    op.drop_table("partner_documents")
    op.drop_index(
        "ix_partner_verifications_status_updated",
        table_name="partner_verifications",
    )
    op.drop_table("partner_verifications")

    op.drop_index("ix_partners_status_updated", table_name="partners")
    op.drop_constraint("fk_partners_reviewed_by_user", "partners", type_="foreignkey")
    op.drop_constraint("fk_partners_created_by_user", "partners", type_="foreignkey")
    op.drop_column("partners", "review_reason")
    op.drop_column("partners", "reviewed_by_user_id")
    op.drop_column("partners", "reviewed_at")
    op.drop_column("partners", "submitted_at")
    op.drop_column("partners", "created_by_user_id")
    op.drop_column("partners", "description")
    op.drop_column("partners", "postal_code")
    op.drop_column("partners", "province")
    op.drop_column("partners", "city")
    op.drop_column("partners", "address_line")
    op.drop_column("partners", "contact_phone")
    op.drop_column("partners", "contact_email")
    op.drop_column("partners", "partner_type")
    op.drop_column("partners", "legal_name")
