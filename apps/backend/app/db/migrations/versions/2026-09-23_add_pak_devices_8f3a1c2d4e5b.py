"""add PAK devices

Revision ID: 8f3a1c2d4e5b
Revises: 630e43f6c848
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f3a1c2d4e5b"
down_revision: str | Sequence[str] | None = "630e43f6c848"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the PAK device table."""
    pak_device_kind = sa.Enum(
        "engineering",
        "otk_line",
        name="pak_device_kind",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "pak_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("kind", pak_device_kind, nullable=False),
        sa.Column("oauth_client_id", sa.String(length=255), nullable=False),
        sa.Column("encrypted_access_key", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_pak_devices"),
        sa.UniqueConstraint("code", name="uq_pak_devices_code"),
        sa.UniqueConstraint("oauth_client_id", name="uq_pak_devices_oauth_client_id"),
    )
    op.create_index("ix_pak_devices_kind", "pak_devices", ["kind"])
    op.create_index("ix_pak_devices_is_active", "pak_devices", ["is_active"])
    op.create_index("ix_pak_devices_archived_at", "pak_devices", ["archived_at"])


def downgrade() -> None:
    """Drop the PAK device table."""
    op.drop_index("ix_pak_devices_archived_at", table_name="pak_devices")
    op.drop_index("ix_pak_devices_is_active", table_name="pak_devices")
    op.drop_index("ix_pak_devices_kind", table_name="pak_devices")
    op.drop_table("pak_devices")
