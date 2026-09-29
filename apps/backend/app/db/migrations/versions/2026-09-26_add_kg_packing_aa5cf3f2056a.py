"""add KG packing

Revision ID: aa5cf3f2056a
Revises: a0949f1503b2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "aa5cf3f2056a"
down_revision: str | Sequence[str] | None = "a0949f1503b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PACKED = sa.text("state = 'packed'")


def upgrade() -> None:
    """Add the packed state of a KG unit with the time and the user who packed it."""
    op.drop_constraint(op.f("ck_kg_units_kg_state"), "kg_units", type_="check")
    op.create_check_constraint(
        op.f("ck_kg_units_kg_state"),
        "kg_units",
        "state IN ('registered', 'packed', 'scrapped')",
    )

    op.add_column("kg_units", sa.Column("packed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("kg_units", sa.Column("packed_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_kg_units_packed_by_id_user_account"),
        "kg_units",
        "user_account",
        ["packed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_kg_units_packed_at_with_packed_state"),
        "kg_units",
        "(state = 'packed') = (packed_at IS NOT NULL)",
    )
    op.create_index(op.f("ix_kg_units_packed_by_id"), "kg_units", ["packed_by_id"])
    op.create_index(op.f("ix_kg_units_packed_batch_id"), "kg_units", ["batch_id"], postgresql_where=PACKED)


def downgrade() -> None:
    """Drop the packed state; fails while packed KG units exist, since packing cannot be undone."""
    op.drop_index(op.f("ix_kg_units_packed_batch_id"), table_name="kg_units", postgresql_where=PACKED)
    op.drop_index(op.f("ix_kg_units_packed_by_id"), table_name="kg_units")
    op.drop_constraint(op.f("ck_kg_units_packed_at_with_packed_state"), "kg_units", type_="check")
    op.drop_constraint(op.f("fk_kg_units_packed_by_id_user_account"), "kg_units", type_="foreignkey")
    op.drop_column("kg_units", "packed_by_id")
    op.drop_column("kg_units", "packed_at")

    op.drop_constraint(op.f("ck_kg_units_kg_state"), "kg_units", type_="check")
    op.create_check_constraint(
        op.f("ck_kg_units_kg_state"),
        "kg_units",
        "state IN ('registered', 'scrapped')",
    )
