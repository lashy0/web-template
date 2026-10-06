"""add multicast groups

Revision ID: 7183dcae0a44
Revises: d0097932f0a2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7183dcae0a44"
down_revision: str | Sequence[str] | None = "d0097932f0a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the multicast group catalog and give every batch one group of each group ID.

    Existing batches have no groups to take, so the database must hold none.
    """
    op.create_table(
        "multicast_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("group_id", sa.SmallInteger(), nullable=False),
        sa.Column("mc_addr", sa.String(length=8), nullable=False),
        sa.Column("mc_key", sa.String(length=32), nullable=False),
        sa.Column("frequency_hz", sa.Integer(), nullable=False),
        sa.Column("datarate", sa.SmallInteger(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("group_id IN (0, 1)", name=op.f("ck_multicast_groups_group_id_range")),
        sa.CheckConstraint("mc_addr ~ '^[0-9a-f]{8}$'", name=op.f("ck_multicast_groups_mc_addr_format")),
        sa.CheckConstraint("mc_key ~ '^[0-9a-f]{32}$'", name=op.f("ck_multicast_groups_mc_key_format")),
        sa.CheckConstraint("frequency_hz > 0", name=op.f("ck_multicast_groups_frequency_hz_positive")),
        sa.CheckConstraint("datarate BETWEEN 0 AND 15", name=op.f("ck_multicast_groups_datarate_range")),
        sa.PrimaryKeyConstraint("id", name="pk_multicast_groups"),
        sa.UniqueConstraint("name", name="uq_multicast_groups_name"),
        sa.UniqueConstraint("mc_addr", name="uq_multicast_groups_mc_addr"),
    )
    op.create_index("ix_multicast_groups_archived_at", "multicast_groups", ["archived_at"])

    for group_id in (0, 1):
        column = f"multicast_group_{group_id}_id"
        op.add_column("batches", sa.Column(column, sa.Uuid(), nullable=False))
        op.create_index(f"ix_batches_{column}", "batches", [column])
        op.create_foreign_key(
            f"fk_batches_{column}_multicast_groups",
            "batches",
            "multicast_groups",
            [column],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    """Drop the multicast groups of batches and their catalog."""
    for group_id in (1, 0):
        column = f"multicast_group_{group_id}_id"
        op.drop_constraint(f"fk_batches_{column}_multicast_groups", "batches", type_="foreignkey")
        op.drop_index(f"ix_batches_{column}", table_name="batches")
        op.drop_column("batches", column)

    op.drop_index("ix_multicast_groups_archived_at", table_name="multicast_groups")
    op.drop_table("multicast_groups")
