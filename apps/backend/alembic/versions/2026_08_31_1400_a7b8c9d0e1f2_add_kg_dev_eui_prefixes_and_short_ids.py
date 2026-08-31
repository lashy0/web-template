"""add KG DevEUI prefixes and short IDs

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_PREFIX = "0000000000"
_LEGACY_SHORT_CODE = "legacy"


def upgrade() -> None:
    """Create DevEUI prefixes and backfill identifiers for existing records."""
    op.create_table(
        "kg_dev_eui_prefixes",
        sa.Column("prefix", sa.String(length=10), nullable=False),
        sa.Column("short_code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("prefix ~ '^[0-9a-f]{10}$'", name="kg_dev_eui_prefix_format"),
        sa.CheckConstraint(
            "short_code ~ '^[a-z0-9]+$'",
            name="kg_dev_eui_prefix_short_code_format",
        ),
        sa.PrimaryKeyConstraint("prefix", name="pk_kg_dev_eui_prefixes"),
        sa.UniqueConstraint("short_code", name="uq_kg_dev_eui_prefixes_short_code"),
    )

    op.execute(
        """
        INSERT INTO kg_dev_eui_prefixes (prefix, short_code, name)
        SELECT DISTINCT left(dev_eui, 10), left(dev_eui, 10), 'Migrated legacy prefix'
        FROM kg_units
        ON CONFLICT (prefix) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO kg_dev_eui_prefixes (prefix, short_code, name)
        VALUES ('{_LEGACY_PREFIX}', '{_LEGACY_SHORT_CODE}', 'Legacy batches without KG')
        ON CONFLICT (prefix) DO NOTHING
        """
    )

    op.add_column(
        "batches",
        sa.Column("dev_eui_prefix", sa.String(length=10), nullable=True),
    )
    op.execute(
        f"""
        UPDATE batches AS batch
        SET dev_eui_prefix = COALESCE(
            (
                SELECT min(left(kg.dev_eui, 10))
                FROM kg_units AS kg
                WHERE kg.batch_id = batch.id
            ),
            '{_LEGACY_PREFIX}'
        )
        """
    )
    op.alter_column("batches", "dev_eui_prefix", nullable=False)
    op.create_foreign_key(
        "fk_batches_dev_eui_prefix_kg_dev_eui_prefixes",
        "batches",
        "kg_dev_eui_prefixes",
        ["dev_eui_prefix"],
        ["prefix"],
    )
    op.create_index("ix_batches_dev_eui_prefix", "batches", ["dev_eui_prefix"])

    op.add_column(
        "kg_units",
        sa.Column("short_id", sa.String(length=20), nullable=True),
    )
    op.execute("UPDATE kg_units SET short_id = dev_eui WHERE short_id IS NULL")
    op.alter_column("kg_units", "short_id", nullable=False)
    op.create_unique_constraint("uq_kg_units_short_id", "kg_units", ["short_id"])


def downgrade() -> None:
    """Remove DevEUI-prefix and short-ID schema changes."""
    op.drop_constraint("uq_kg_units_short_id", "kg_units", type_="unique")
    op.drop_column("kg_units", "short_id")

    op.drop_index("ix_batches_dev_eui_prefix", table_name="batches")
    op.drop_constraint(
        "fk_batches_dev_eui_prefix_kg_dev_eui_prefixes",
        "batches",
        type_="foreignkey",
    )
    op.drop_column("batches", "dev_eui_prefix")

    op.drop_table("kg_dev_eui_prefixes")
