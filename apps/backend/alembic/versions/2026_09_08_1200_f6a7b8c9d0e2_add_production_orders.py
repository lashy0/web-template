"""Add production orders and optional batch membership.

Revision ID: f6a7b8c9d0e2
Revises: e5f6a7b8c9d0
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6a7b8c9d0e2"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "production_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_production_orders"),
    )
    op.create_index("ix_production_orders_archived_at", "production_orders", ["archived_at"])
    op.create_index("ix_production_orders_created_at", "production_orders", ["created_at"])
    op.add_column("batches", sa.Column("production_order_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_batches_production_order_id_production_orders",
        "batches",
        "production_orders",
        ["production_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_batches_production_order_id", "batches", ["production_order_id"])


def downgrade() -> None:
    op.drop_index("ix_batches_production_order_id", table_name="batches")
    op.drop_constraint(
        "fk_batches_production_order_id_production_orders", "batches", type_="foreignkey"
    )
    op.drop_column("batches", "production_order_id")
    op.drop_index("ix_production_orders_created_at", table_name="production_orders")
    op.drop_index("ix_production_orders_archived_at", table_name="production_orders")
    op.drop_table("production_orders")
