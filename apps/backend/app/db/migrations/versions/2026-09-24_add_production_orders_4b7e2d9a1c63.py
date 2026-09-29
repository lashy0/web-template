"""add production orders

Revision ID: 4b7e2d9a1c63
Revises: 8f3a1c2d4e5b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4b7e2d9a1c63"
down_revision: str | Sequence[str] | None = "8f3a1c2d4e5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the production order table."""
    op.create_table(
        "production_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_production_orders"),
    )
    op.create_index("ix_production_orders_archived_at", "production_orders", ["archived_at"])


def downgrade() -> None:
    """Drop the production order table."""
    op.drop_index("ix_production_orders_archived_at", table_name="production_orders")
    op.drop_table("production_orders")
