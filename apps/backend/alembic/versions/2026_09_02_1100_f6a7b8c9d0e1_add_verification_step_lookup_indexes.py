"""link verification steps to PAK tests

Revision ID: f6a7b8c9d0e1
Revises: e4f5a6b7c8d9
Create Date: 2026-09-02 11:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Link verification steps to PAK test and defect group records."""
    op.add_column(
        "verification_steps",
        sa.Column("pak_test_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "verification_steps",
        sa.Column("defect_group_id", sa.Uuid(), nullable=False),
    )
    op.alter_column(
        "verification_steps",
        "test_label",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "verification_steps",
        "error_group_code",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_verification_steps_pak_test_id_pak_tests",
        "verification_steps",
        "pak_tests",
        ["pak_test_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_verification_steps_defect_group_id_defect_groups",
        "verification_steps",
        "defect_groups",
        ["defect_group_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_verification_steps_pak_test_id",
        "verification_steps",
        ["pak_test_id"],
    )
    op.create_index(
        "ix_verification_steps_defect_group_id",
        "verification_steps",
        ["defect_group_id"],
    )


def downgrade() -> None:
    """Remove verification step links to catalog records."""
    op.drop_index(
        "ix_verification_steps_defect_group_id",
        table_name="verification_steps",
    )
    op.drop_index(
        "ix_verification_steps_pak_test_id",
        table_name="verification_steps",
    )
    op.drop_constraint(
        "fk_verification_steps_defect_group_id_defect_groups",
        "verification_steps",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_verification_steps_pak_test_id_pak_tests",
        "verification_steps",
        type_="foreignkey",
    )
    op.alter_column(
        "verification_steps",
        "error_group_code",
        existing_type=sa.String(length=32),
        nullable=True,
    )
    op.alter_column(
        "verification_steps",
        "test_label",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.drop_column("verification_steps", "defect_group_id")
    op.drop_column("verification_steps", "pak_test_id")
