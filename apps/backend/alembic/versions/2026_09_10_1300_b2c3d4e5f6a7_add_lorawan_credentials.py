"""add encrypted LoRaWAN credentials for KG units

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lorawan_credentials",
        sa.Column("kg_dev_eui", sa.String(length=16), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("encrypted_data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["kg_dev_eui"], ["kg_units.dev_eui"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("kg_dev_eui"),
    )


def downgrade() -> None:
    op.drop_table("lorawan_credentials")
