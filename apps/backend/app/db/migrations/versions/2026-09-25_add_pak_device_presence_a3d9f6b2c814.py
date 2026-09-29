"""move PAK last-seen time to its own table

Revision ID: a3d9f6b2c814
Revises: 5e8a3c1f7b42
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3d9f6b2c814"
down_revision: str | Sequence[str] | None = "5e8a3c1f7b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record PAK presence apart from the device row, keeping the known times."""
    op.create_table(
        "pak_device_presence",
        sa.Column("pak_id", sa.Uuid(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["pak_id"],
            ["pak_devices.id"],
            name="fk_pak_device_presence_pak_id_pak_devices",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pak_id", name="pk_pak_device_presence"),
    )
    op.execute(
        "INSERT INTO pak_device_presence (pak_id, last_seen_at) "
        "SELECT id, last_seen_at FROM pak_devices WHERE last_seen_at IS NOT NULL"
    )
    op.drop_column("pak_devices", "last_seen_at")


def downgrade() -> None:
    """Put the last-seen time back on the device row."""
    op.add_column("pak_devices", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE pak_devices SET last_seen_at = presence.last_seen_at "
        "FROM pak_device_presence AS presence WHERE presence.pak_id = pak_devices.id"
    )
    op.drop_table("pak_device_presence")
