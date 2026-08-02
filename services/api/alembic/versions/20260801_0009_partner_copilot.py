"""Add Partner Copilot analytics, insight, session, feedback, usage, and schedule tables.

Revision ID: 20260801_0009
Revises: 20260801_0008
"""
import uuid
from collections.abc import Sequence
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "20260801_0009"
down_revision: str | None = "20260801_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = (
    ("6a6098a1-d986-4b13-9c48-000000000071", "partner.copilot.read"),
    ("6a6098a1-d986-4b13-9c48-000000000072", "partner.copilot.write"),
    ("6a6098a1-d986-4b13-9c48-000000000073", "partner.copilot.chat"),
    ("6a6098a1-d986-4b13-9c48-000000000074", "partner.copilot.feedback"),
    ("6a6098a1-d986-4b13-9c48-000000000075", "platform.copilot.read"),
    ("6a6098a1-d986-4b13-9c48-000000000076", "platform.copilot.manage"),
)

def seed_permission(permission_id: str, code: str) -> None:
    op.execute(sa.text("INSERT INTO permissions (id, code) VALUES (:id, :code) ON CONFLICT (code) DO NOTHING").bindparams(sa.bindparam("id", value=uuid.UUID(permission_id), type_=postgresql.UUID(as_uuid=True)), code=code))

def grant(role: str, code: str) -> None:
    op.execute(sa.text("INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r, permissions p WHERE r.code=:role AND p.code=:code ON CONFLICT (role_id, permission_id) DO NOTHING").bindparams(role=role, code=code))

def partner_rls(table: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")); op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    expression = f"current_setting('app.is_platform_admin', true)='true' OR COALESCE(current_setting('app.user_id', true),'')='' OR EXISTS (SELECT 1 FROM partner_memberships m WHERE m.partner_id={table}.partner_id AND m.user_id=NULLIF(current_setting('app.user_id', true),'')::uuid AND m.status='active')"
    op.execute(sa.text(f"CREATE POLICY {table}_partner_scope ON {table} FOR ALL USING ({expression}) WITH CHECK ({expression})"))

def upgrade() -> None:
    op.create_table("partner_metric_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False), sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comparison_start", sa.DateTime(timezone=True), nullable=False), sa.Column("comparison_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(3), server_default="IDR", nullable=False), sa.Column("metrics", postgresql.JSONB(), nullable=False), sa.Column("comparison_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("engine_version", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("partner_id", "period_start", "period_end", name="uq_partner_metric_snapshot_period"), sa.CheckConstraint("period_end > period_start", name="ck_partner_metric_snapshots_period"))
    op.create_index("ix_partner_metric_snapshots_partner_created", "partner_metric_snapshots", ["partner_id", "created_at"])
    op.create_table("partner_copilot_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False), sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_metric_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False), sa.Column("severity", sa.String(20), nullable=False), sa.Column("title", sa.String(180), nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("recommendation", sa.Text(), nullable=False), sa.Column("evidence", postgresql.JSONB(), nullable=False), sa.Column("status", sa.String(20), server_default="active", nullable=False), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("dismissed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("category IN ('revenue','booking','inventory','finance','operations')", name="ck_partner_copilot_insights_category"), sa.CheckConstraint("severity IN ('info','warning','critical')", name="ck_partner_copilot_insights_severity"), sa.CheckConstraint("status IN ('active','dismissed')", name="ck_partner_copilot_insights_status"))
    op.create_index("ix_partner_copilot_insights_partner_status", "partner_copilot_insights", ["partner_id", "status", "generated_at"])
    op.create_table("partner_copilot_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False), sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("title", sa.String(180), nullable=False), sa.Column("status", sa.String(20), server_default="active", nullable=False), sa.Column("context", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.CheckConstraint("status IN ('active','closed')", name="ck_partner_copilot_sessions_status"))
    op.create_index("ix_partner_copilot_sessions_partner_updated", "partner_copilot_sessions", ["partner_id", "updated_at"])
    op.create_table("partner_copilot_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_copilot_sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("role", sa.String(20), nullable=False), sa.Column("intent", sa.String(30)), sa.Column("content", sa.Text(), nullable=False), sa.Column("evidence", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("model_provider", sa.String(50), server_default="local", nullable=False), sa.Column("model_version", sa.String(80), nullable=False), sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False), sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False), sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.CheckConstraint("role IN ('user','assistant','tool')", name="ck_partner_copilot_messages_role"), sa.CheckConstraint("input_tokens >= 0 AND output_tokens >= 0 AND latency_ms >= 0", name="ck_partner_copilot_messages_usage"))
    op.create_index("ix_partner_copilot_messages_session_created", "partner_copilot_messages", ["session_id", "created_at"])
    op.create_table("partner_copilot_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_copilot_messages.id", ondelete="CASCADE"), nullable=False), sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_copilot_sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("rating", sa.Integer(), nullable=False), sa.Column("helpful", sa.Boolean(), nullable=False), sa.Column("comment", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("message_id", "user_id", name="uq_partner_copilot_feedback_message_user"), sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_partner_copilot_feedback_rating"))
    op.create_table("partner_copilot_usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partner_copilot_sessions.id", ondelete="SET NULL")), sa.Column("action", sa.String(50), nullable=False), sa.Column("model_provider", sa.String(50), nullable=False), sa.Column("model_version", sa.String(80), nullable=False), sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False), sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False), sa.Column("estimated_cost_minor", sa.BigInteger(), server_default="0", nullable=False), sa.Column("currency", sa.String(3), server_default="IDR", nullable=False), sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False), sa.Column("usage_metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.CheckConstraint("input_tokens >= 0 AND output_tokens >= 0 AND estimated_cost_minor >= 0 AND latency_ms >= 0", name="ck_partner_copilot_usage_nonnegative"))
    op.create_index("ix_partner_copilot_usage_partner_created", "partner_copilot_usage_logs", ["partner_id", "created_at"])
    op.create_table("partner_copilot_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False), sa.Column("cadence", sa.String(20), server_default="weekly", nullable=False), sa.Column("timezone", sa.String(64), server_default="Asia/Jakarta", nullable=False), sa.Column("weekday", sa.Integer(), server_default="0", nullable=False), sa.Column("hour", sa.Integer(), server_default="8", nullable=False), sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False), sa.Column("last_run_at", sa.DateTime(timezone=True)), sa.Column("next_run_at", sa.DateTime(timezone=True)), sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("partner_id", name="uq_partner_copilot_schedules_partner"), sa.CheckConstraint("cadence IN ('weekly')", name="ck_partner_copilot_schedules_cadence"), sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_partner_copilot_schedules_weekday"), sa.CheckConstraint("hour BETWEEN 0 AND 23", name="ck_partner_copilot_schedules_hour"))
    for table in ("partner_metric_snapshots", "partner_copilot_insights", "partner_copilot_sessions", "partner_copilot_messages", "partner_copilot_feedback", "partner_copilot_usage_logs", "partner_copilot_schedules"): partner_rls(table)
    for permission_id, code in PERMISSIONS: seed_permission(permission_id, code)
    for role in ("partner_owner", "partner_admin"):
        for code in ("partner.copilot.read", "partner.copilot.write", "partner.copilot.chat", "partner.copilot.feedback"): grant(role, code)
    for code in ("platform.copilot.read", "platform.copilot.manage"): grant("super_admin", code)
    grant("platform_support", "platform.copilot.read")

def downgrade() -> None:
    for table in ("partner_copilot_schedules", "partner_copilot_usage_logs", "partner_copilot_feedback", "partner_copilot_messages", "partner_copilot_sessions", "partner_copilot_insights", "partner_metric_snapshots"): op.drop_table(table)
    codes = [code for _, code in PERMISSIONS]
    op.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = ANY(:codes))").bindparams(sa.bindparam("codes", value=codes, type_=postgresql.ARRAY(sa.String()))))
    op.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(sa.bindparam("codes", value=codes, type_=postgresql.ARRAY(sa.String()))))
