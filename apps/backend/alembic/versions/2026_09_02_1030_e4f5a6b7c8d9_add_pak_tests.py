"""add PAK test catalog

Revision ID: e4f5a6b7c8d9
Revises: 503f387ba323
Create Date: 2026-09-02 10:30:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: str | Sequence[str] | None = "503f387ba323"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create PAK test catalog storage."""
    op.create_table(
        "pak_tests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("test_label", sa.String(length=255), nullable=False),
        sa.Column("defect_group_id", sa.Uuid(), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["defect_group_id"],
            ["defect_groups.id"],
            name=op.f("fk_pak_tests_defect_group_id_defect_groups"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pak_tests")),
        sa.UniqueConstraint("test_name", name=op.f("uq_pak_tests_test_name")),
    )
    op.create_index("ix_pak_tests_defect_group_id", "pak_tests", ["defect_group_id"])


def downgrade() -> None:
    """Remove PAK test catalog storage."""
    op.drop_index("ix_pak_tests_defect_group_id", table_name="pak_tests")
    op.drop_table("pak_tests")
