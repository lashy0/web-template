"""add KG versions and link batches

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the KG-version catalogue and optional batch reference."""
    op.create_table(
        "kg_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_kg_versions"),
        sa.UniqueConstraint("code", name="uq_kg_versions_code"),
    )
    op.create_index("ix_kg_versions_archived_at", "kg_versions", ["archived_at"])
    op.add_column("batches", sa.Column("kg_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_batches_kg_version_id_kg_versions",
        "batches",
        "kg_versions",
        ["kg_version_id"],
        ["id"],
    )
    op.create_index("ix_batches_kg_version_id", "batches", ["kg_version_id"])


def downgrade() -> None:
    """Remove the KG-version catalogue and batch reference."""
    op.drop_index("ix_batches_kg_version_id", table_name="batches")
    op.drop_constraint("fk_batches_kg_version_id_kg_versions", "batches", type_="foreignkey")
    op.drop_column("batches", "kg_version_id")
    op.drop_index("ix_kg_versions_archived_at", table_name="kg_versions")
    op.drop_table("kg_versions")
