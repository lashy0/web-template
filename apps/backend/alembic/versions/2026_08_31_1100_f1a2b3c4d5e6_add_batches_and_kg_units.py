"""add batches and kg units

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create batch-management and KG-unit tables."""
    batch_status = sa.Enum(
        "IN_PRODUCTION",
        "COMPLETED",
        name="batch_status",
        native_enum=False,
        create_constraint=True,
    )
    kg_status = sa.Enum(
        "REGISTERED",
        "TESTING",
        "TEST_FAILED",
        "IN_ENGINEER_REPAIR",
        "IN_PRODUCTION_REPAIR",
        "READY_FOR_RETEST",
        "READY_FOR_PACKING",
        "PACKED",
        "SHIPPED",
        "SCRAPPED",
        name="kg_status",
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
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("planned_qty  > 0", name="batch_planned_qty_positive"),
        sa.CheckConstraint("day_plan_qty  > 0", name="batch_day_plan_qty_positive"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_batches_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_batches"),
    )
    op.create_index("ix_batches_status", "batches", ["status"])
    op.create_index("ix_batches_created_at", "batches", ["created_at"])
    op.create_index("ix_batches_archived_at", "batches", ["archived_at"])

    op.create_table(
        "kg_units",
        sa.Column("dev_eui", sa.String(length=16), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("status", kg_status, nullable=False),
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
        sa.CheckConstraint("dev_eui ~ '^[0-9a-f]{16}$'", name="dev_eui_format"),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name="fk_kg_units_batch_id_batches",
        ),
        sa.PrimaryKeyConstraint("dev_eui", name="pk_kg_units"),
    )
    op.create_index("ix_kg_units_batch_id", "kg_units", ["batch_id"])
    op.create_index("ix_kg_units_status", "kg_units", ["status"])

    op.create_table(
        "batch_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("quantity > 0", name="batch_receipt_quantity_positive"),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name="fk_batch_receipts_batch_id_batches",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_batch_receipts_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_batch_receipts"),
    )
    op.create_index(
        "ix_batch_receipts_batch_created_at",
        "batch_receipts",
        ["batch_id", "created_at"],
    )
    op.create_index("ix_batch_receipts_voided_at", "batch_receipts", ["voided_at"])

    op.create_table(
        "batch_shipments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name="fk_batch_shipments_batch_id_batches",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_batch_shipments_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_batch_shipments"),
    )
    op.create_index(
        "ix_batch_shipments_batch_created_at",
        "batch_shipments",
        ["batch_id", "created_at"],
    )
    op.create_index("ix_batch_shipments_voided_at", "batch_shipments", ["voided_at"])

    op.create_table(
        "batch_shipment_items",
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("kg_dev_eui", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["batch_shipments.id"],
            name="fk_batch_shipment_items_shipment_id_batch_shipments",
        ),
        sa.ForeignKeyConstraint(
            ["kg_dev_eui"],
            ["kg_units.dev_eui"],
            name="fk_batch_shipment_items_kg_dev_eui_kg_units",
        ),
        sa.PrimaryKeyConstraint("shipment_id", "kg_dev_eui", name="pk_batch_shipment_items"),
    )
    op.create_index(
        "ix_batch_shipment_items_kg_dev_eui",
        "batch_shipment_items",
        ["kg_dev_eui"],
    )


def downgrade() -> None:
    """Remove batch-management and KG-unit tables."""
    op.drop_index("ix_batch_shipment_items_kg_dev_eui", table_name="batch_shipment_items")
    op.drop_table("batch_shipment_items")

    op.drop_index("ix_batch_shipments_voided_at", table_name="batch_shipments")
    op.drop_index("ix_batch_shipments_batch_created_at", table_name="batch_shipments")
    op.drop_table("batch_shipments")

    op.drop_index("ix_batch_receipts_voided_at", table_name="batch_receipts")
    op.drop_index("ix_batch_receipts_batch_created_at", table_name="batch_receipts")
    op.drop_table("batch_receipts")

    op.drop_index("ix_kg_units_status", table_name="kg_units")
    op.drop_index("ix_kg_units_batch_id", table_name="kg_units")
    op.drop_table("kg_units")

    op.drop_index("ix_batches_archived_at", table_name="batches")
    op.drop_index("ix_batches_created_at", table_name="batches")
    op.drop_index("ix_batches_status", table_name="batches")
    op.drop_table("batches")
