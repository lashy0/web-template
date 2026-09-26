"""add defect catalog

Revision ID: c71e4b9d2a05
Revises: a3d9f6b2c814
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c71e4b9d2a05"
down_revision: str | Sequence[str] | None = "a3d9f6b2c814"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create defect groups and the defect types inside them."""
    op.create_table(
        "defect_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_defect_groups"),
        sa.UniqueConstraint("code", name="uq_defect_groups_code"),
    )
    op.create_index("ix_defect_groups_archived_at", "defect_groups", ["archived_at"])

    op.create_table(
        "defect_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("possible_cause", sa.Text(), nullable=True),
        sa.Column("engineer_action", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["defect_groups.id"],
            name="fk_defect_types_group_id_defect_groups",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_defect_types"),
        sa.UniqueConstraint("code", name="uq_defect_types_code"),
    )
    op.create_index("ix_defect_types_group_id", "defect_types", ["group_id"])
    op.create_index("ix_defect_types_archived_at", "defect_types", ["archived_at"])


def downgrade() -> None:
    """Drop the defect catalog."""
    op.drop_index("ix_defect_types_archived_at", table_name="defect_types")
    op.drop_index("ix_defect_types_group_id", table_name="defect_types")
    op.drop_table("defect_types")
    op.drop_index("ix_defect_groups_archived_at", table_name="defect_groups")
    op.drop_table("defect_groups")
