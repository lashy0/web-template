"""lowercase PAK device kind values

Revision ID: b1c2d3e4f5a6
Revises: f6a7b8c9d0e1
Create Date: 2026-09-04 12:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE pak_devices DROP CONSTRAINT IF EXISTS ck_pak_devices_pak_device_kind")
    op.execute("ALTER TABLE pak_devices DROP CONSTRAINT IF EXISTS pak_device_kind")
    op.execute("UPDATE pak_devices SET kind = lower(kind)")
    op.create_check_constraint(
        "ck_pak_devices_pak_device_kind",
        "pak_devices",
        "kind IN ('engineering', 'otk_line')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pak_devices_pak_device_kind", "pak_devices", type_="check")
    op.execute("UPDATE pak_devices SET kind = upper(kind)")
    op.create_check_constraint(
        "ck_pak_devices_pak_device_kind",
        "pak_devices",
        "kind IN ('ENGINEERING', 'OTK_LINE')",
    )
