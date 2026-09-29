"""add KG prefixes and versions

Revision ID: 7c1f5e3a9b28
Revises: 4b7e2d9a1c63
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c1f5e3a9b28"
down_revision: str | Sequence[str] | None = "4b7e2d9a1c63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the KG prefix and KG version catalogs."""
    op.create_table(
        "kg_prefixes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("prefix", sa.String(length=10), nullable=False),
        sa.Column("short_code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("prefix ~ '^[0-9a-f]{10}$'", name=op.f("ck_kg_prefixes_prefix_format")),
        sa.CheckConstraint("short_code ~ '^[a-z0-9]+$'", name=op.f("ck_kg_prefixes_short_code_format")),
        sa.PrimaryKeyConstraint("id", name="pk_kg_prefixes"),
        sa.UniqueConstraint("prefix", name="uq_kg_prefixes_prefix"),
        sa.UniqueConstraint("short_code", name="uq_kg_prefixes_short_code"),
    )
    op.create_index("ix_kg_prefixes_archived_at", "kg_prefixes", ["archived_at"])

    op.create_table(
        "kg_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_kg_versions"),
        sa.UniqueConstraint("code", name="uq_kg_versions_code"),
    )
    op.create_index("ix_kg_versions_archived_at", "kg_versions", ["archived_at"])


def downgrade() -> None:
    """Drop the KG catalogs."""
    op.drop_index("ix_kg_versions_archived_at", table_name="kg_versions")
    op.drop_table("kg_versions")
    op.drop_index("ix_kg_prefixes_archived_at", table_name="kg_prefixes")
    op.drop_table("kg_prefixes")
