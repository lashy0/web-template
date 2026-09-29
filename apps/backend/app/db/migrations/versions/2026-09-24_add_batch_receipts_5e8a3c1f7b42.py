"""add batch receipts

Revision ID: 5e8a3c1f7b42
Revises: 2d63d1710b9c
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e8a3c1f7b42"
down_revision: str | Sequence[str] | None = "2d63d1710b9c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the receipts of KG units received from batches."""
    op.create_table(
        "batch_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_batch_receipts_quantity_positive")),
        sa.CheckConstraint(
            "(voided_at IS NULL) = (void_reason IS NULL)",
            name=op.f("ck_batch_receipts_void_reason_with_voided_at"),
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name="fk_batch_receipts_batch_id_batches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user_account.id"],
            name="fk_batch_receipts_created_by_id_user_account",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_batch_receipts"),
    )
    op.create_index("ix_batch_receipts_batch_id_created_at", "batch_receipts", ["batch_id", "created_at"])
    op.create_index("ix_batch_receipts_created_by_id", "batch_receipts", ["created_by_id"])


def downgrade() -> None:
    """Drop the batch receipts."""
    op.drop_index("ix_batch_receipts_created_by_id", table_name="batch_receipts")
    op.drop_index("ix_batch_receipts_batch_id_created_at", table_name="batch_receipts")
    op.drop_table("batch_receipts")
