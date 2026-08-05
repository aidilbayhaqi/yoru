"""Persist checkout shipping address and method snapshots.

Revision ID: 20260805_0011
Revises: 20260802_0010
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260805_0011"
down_revision: str | None = "20260802_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "checkout_quotes",
        sa.Column("shipping_address_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "checkout_quotes",
        sa.Column("shipping_method_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("shipping_address_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("shipping_method_snapshot", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "shipping_method_snapshot")
    op.drop_column("orders", "shipping_address_snapshot")
    op.drop_column("checkout_quotes", "shipping_method_snapshot")
    op.drop_column("checkout_quotes", "shipping_address_snapshot")
