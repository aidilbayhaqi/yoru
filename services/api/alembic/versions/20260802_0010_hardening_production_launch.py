"""Add production operations, security-event, and launch-gate tables.

Revision ID: 20260802_0010
Revises: 20260801_0009
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260802_0010"
down_revision: str | None = "20260801_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = (
    ("6a6098a1-d986-4b13-9c48-000000000081", "platform.ops.read"),
    ("6a6098a1-d986-4b13-9c48-000000000082", "platform.ops.manage"),
    ("6a6098a1-d986-4b13-9c48-000000000083", "platform.security.read"),
    ("6a6098a1-d986-4b13-9c48-000000000084", "platform.security.manage"),
)


def seed_permission(permission_id: str, code: str) -> None:
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
            code=code,
        )
    )


def grant(role: str, code: str) -> None:
    op.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.code=:role AND p.code=:code "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        ).bindparams(role=role, code=code)
    )


def platform_rls(table: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    expression = (
        "current_setting('app.is_platform_admin', true)='true' "
        "OR COALESCE(current_setting('app.user_id', true),'')=''"
    )
    op.execute(
        sa.text(
            f"CREATE POLICY {table}_platform_scope ON {table} FOR ALL "
            f"USING ({expression}) WITH CHECK ({expression})"
        )
    )


def upgrade() -> None:
    op.create_table(
        "ops_job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), server_default="running", nullable=False),
        sa.Column(
            "started_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column(
            "summary",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "job_type IN ('retention','restore_drill','launch_gate','dependency_audit','security_scan')",
            name="ck_ops_job_runs_type",
        ),
        sa.CheckConstraint(
            "status IN ('running','completed','failed')",
            name="ck_ops_job_runs_status",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_ops_job_runs_duration",
        ),
    )
    op.create_index(
        "ix_ops_job_runs_type_started", "ops_job_runs", ["job_type", "started_at"]
    )

    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("request_id", sa.String(128)),
        sa.Column("ip_prefix", sa.String(80)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "resolved_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("resolution_note", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('info','low','medium','high','critical')",
            name="ck_security_events_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open','acknowledged','resolved')",
            name="ck_security_events_status",
        ),
    )
    op.create_index(
        "ix_security_events_status_severity",
        "security_events",
        ["status", "severity", "occurred_at"],
    )

    op.create_table(
        "launch_gate_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("release_version", sa.String(40), nullable=False),
        sa.Column("expected_alembic_head", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("checks", postgresql.JSONB(), nullable=False),
        sa.Column(
            "evaluated_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pass','warn','fail')", name="ck_launch_gate_status"
        ),
    )
    op.create_index(
        "ix_launch_gate_evaluations_created",
        "launch_gate_evaluations",
        ["evaluated_at"],
    )

    for table in ("ops_job_runs", "security_events", "launch_gate_evaluations"):
        platform_rls(table)

    for permission_id, code in PERMISSIONS:
        seed_permission(permission_id, code)
    for code in (
        "platform.ops.read",
        "platform.ops.manage",
        "platform.security.read",
        "platform.security.manage",
    ):
        grant("super_admin", code)
    for code in ("platform.ops.read", "platform.security.read"):
        grant("platform_support", code)
        grant("platform_verifier", code)


def downgrade() -> None:
    for table in (
        "launch_gate_evaluations",
        "security_events",
        "ops_job_runs",
    ):
        op.drop_table(table)

    codes = [code for _, code in PERMISSIONS]
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(
            sa.bindparam("codes", value=codes, type_=postgresql.ARRAY(sa.String()))
        )
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(
            sa.bindparam("codes", value=codes, type_=postgresql.ARRAY(sa.String()))
        )
    )
