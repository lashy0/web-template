"""add batches and KG units

Revision ID: 2d63d1710b9c
Revises: 7c1f5e3a9b28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2d63d1710b9c"
down_revision: str | Sequence[str] | None = "7c1f5e3a9b28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEV_EUI_SERIAL_MAX = 0xFFFFFF


def upgrade() -> None:
    """Create batches with their KG units and the DevEUI counter of each prefix."""
    op.add_column(
        "kg_prefixes",
        sa.Column("next_serial", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        "ck_kg_prefixes_next_serial_range",
        "kg_prefixes",
        f"next_serial BETWEEN 1 AND {DEV_EUI_SERIAL_MAX + 1}",
    )

    batch_status = sa.Enum(
        "in_production",
        "completed",
        name="batch_status",
        native_enum=False,
        create_constraint=True,
    )
    activation_type = sa.Enum(
        "otaa",
        "abp",
        name="activation_type",
        native_enum=False,
        create_constraint=True,
    )
    lorawan_version = sa.Enum(
        "1.0",
        "1.1",
        name="lorawan_version",
        native_enum=False,
        create_constraint=True,
    )
    kg_state = sa.Enum(
        "registered",
        "scrapped",
        name="kg_state",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("planned_qty", sa.Integer(), nullable=False),
        sa.Column("day_plan_qty", sa.Integer(), nullable=False),
        sa.Column("status", batch_status, nullable=False),
        sa.Column("kg_prefix_id", sa.Uuid(), nullable=False),
        sa.Column("first_serial", sa.Integer(), nullable=False),
        sa.Column("kg_version_id", sa.Uuid(), nullable=True),
        sa.Column("production_order_id", sa.Uuid(), nullable=True),
        sa.Column("activation_type", activation_type, nullable=False),
        sa.Column("lorawan_version", lorawan_version, nullable=False),
        sa.Column("join_eui", sa.String(length=16), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("planned_qty > 0", name="ck_batches_planned_qty_positive"),
        sa.CheckConstraint("day_plan_qty > 0", name="ck_batches_day_plan_qty_positive"),
        sa.CheckConstraint(
            f"first_serial >= 1 AND first_serial + planned_qty - 1 <= {DEV_EUI_SERIAL_MAX}",
            name="ck_batches_serial_range",
        ),
        sa.CheckConstraint("join_eui ~ '^[0-9a-f]{16}$'", name="ck_batches_join_eui_format"),
        sa.ForeignKeyConstraint(
            ["kg_prefix_id"],
            ["kg_prefixes.id"],
            name="fk_batches_kg_prefix_id_kg_prefixes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kg_version_id"],
            ["kg_versions.id"],
            name="fk_batches_kg_version_id_kg_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_order_id"],
            ["production_orders.id"],
            name="fk_batches_production_order_id_production_orders",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user_account.id"],
            name="fk_batches_created_by_id_user_account",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_batches"),
        sa.UniqueConstraint("join_eui", name="uq_batches_join_eui"),
    )
    op.create_index("ix_batches_kg_prefix_id", "batches", ["kg_prefix_id"])
    op.create_index("ix_batches_kg_version_id", "batches", ["kg_version_id"])
    op.create_index("ix_batches_production_order_id", "batches", ["production_order_id"])
    op.create_index("ix_batches_created_by_id", "batches", ["created_by_id"])

    op.create_table(
        "kg_units",
        sa.Column("dev_eui", sa.String(length=16), nullable=False),
        sa.Column("short_id", sa.String(length=20), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("state", kg_state, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("dev_eui ~ '^[0-9a-f]{16}$'", name="ck_kg_units_dev_eui_format"),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name="fk_kg_units_batch_id_batches",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dev_eui", name="pk_kg_units"),
        sa.UniqueConstraint("short_id", name="uq_kg_units_short_id"),
    )
    op.create_index("ix_kg_units_batch_id", "kg_units", ["batch_id"])


def downgrade() -> None:
    """Drop batches and KG units; the DevEUI counters are lost."""
    op.drop_index("ix_kg_units_batch_id", table_name="kg_units")
    op.drop_table("kg_units")
    op.drop_index("ix_batches_created_by_id", table_name="batches")
    op.drop_index("ix_batches_production_order_id", table_name="batches")
    op.drop_index("ix_batches_kg_version_id", table_name="batches")
    op.drop_index("ix_batches_kg_prefix_id", table_name="batches")
    op.drop_table("batches")
    op.drop_constraint("ck_kg_prefixes_next_serial_range", "kg_prefixes", type_="check")
    op.drop_column("kg_prefixes", "next_serial")
