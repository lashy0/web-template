"""add immutable LoRaWAN configuration for batches

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e2
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "batch_lorawan_configs",
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("activation_type", sa.String(length=4), nullable=False),
        sa.Column("lorawan_version", sa.String(length=3), nullable=False),
        sa.Column("join_eui", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "activation_type IN ('otaa', 'abp')",
            name="activation_type",
        ),
        sa.CheckConstraint(
            "lorawan_version IN ('1.0', '1.1')",
            name="lorawan_version",
        ),
        sa.CheckConstraint(
            "join_eui ~ '^[0-9a-f]{16}$'",
            name="batch_lorawan_config_join_eui_format",
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("batch_id"),
        sa.UniqueConstraint("join_eui"),
    )


def downgrade() -> None:
    op.drop_table("batch_lorawan_configs")
