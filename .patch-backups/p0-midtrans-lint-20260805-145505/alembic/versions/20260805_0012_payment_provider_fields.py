"""Add provider status and payment actions.

Revision ID: 20260805_0012
Revises: 20260805_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0012"
down_revision: str | None = "20260805_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_orders_payment_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_payment_status",
        "orders",
        "payment_status IN ('pending', 'paid', 'failed', 'cancelled', 'refunded', "
        "'partially_refunded', 'expired')",
    )
    op.add_column(
        "payment_intents",
        sa.Column("provider_status", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "payment_intents",
        sa.Column(
            "actions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("payment_intents", "actions", server_default=None)


def downgrade() -> None:
    op.drop_column("payment_intents", "actions")
    op.drop_column("payment_intents", "provider_status")
    op.drop_constraint("ck_orders_payment_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_payment_status",
        "orders",
        "payment_status IN ('pending', 'paid', 'failed', 'cancelled', 'refunded', "
        "'partially_refunded')",
    )
