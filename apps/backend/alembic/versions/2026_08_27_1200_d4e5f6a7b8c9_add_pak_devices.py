"""add PAK devices with encrypted access keys

Revision ID: d4e5f6a7b8c9
Revises: b3c4d5e6f7a8
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pak_device_kind = sa.Enum(
        "ENGINEERING",
        "OTK_LINE",
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="pk_pak_devices"),
        sa.UniqueConstraint("code", name="uq_pak_devices_code"),
        sa.UniqueConstraint("oauth_client_id", name="uq_pak_devices_oauth_client_id"),
    )
    op.create_index("ix_pak_devices_code", "pak_devices", ["code"])
    op.create_index("ix_pak_devices_oauth_client_id", "pak_devices", ["oauth_client_id"])
    op.create_index("ix_pak_devices_kind", "pak_devices", ["kind"])
    op.create_index("ix_pak_devices_is_active", "pak_devices", ["is_active"])
    op.create_index("ix_pak_devices_archived_at", "pak_devices", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_pak_devices_archived_at", table_name="pak_devices")
    op.drop_index("ix_pak_devices_is_active", table_name="pak_devices")
    op.drop_index("ix_pak_devices_kind", table_name="pak_devices")
    op.drop_index("ix_pak_devices_oauth_client_id", table_name="pak_devices")
    op.drop_index("ix_pak_devices_code", table_name="pak_devices")
    op.drop_table("pak_devices")
