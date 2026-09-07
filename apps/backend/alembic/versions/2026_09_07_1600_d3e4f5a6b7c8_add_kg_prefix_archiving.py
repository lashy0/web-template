"""add KG DevEUI prefix archiving

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add a soft-archive timestamp and index for DevEUI prefixes."""
    op.add_column(
        "kg_dev_eui_prefixes",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_kg_dev_eui_prefixes_archived_at",
        "kg_dev_eui_prefixes",
        ["archived_at"],
    )


def downgrade() -> None:
    """Remove the DevEUI prefix archive state."""
    op.drop_index("ix_kg_dev_eui_prefixes_archived_at", table_name="kg_dev_eui_prefixes")
    op.drop_column("kg_dev_eui_prefixes", "archived_at")
