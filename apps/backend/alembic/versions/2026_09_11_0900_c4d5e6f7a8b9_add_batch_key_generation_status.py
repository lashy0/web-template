"""add background key generation status to batches

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "batches",
        sa.Column(
            "key_generation_status",
            sa.String(length=9),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.create_check_constraint(
        "batch_key_generation_status",
        "batches",
        "key_generation_status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("batch_key_generation_status", "batches", type_="check")
    op.drop_column("batches", "key_generation_status")
