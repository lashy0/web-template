"""add batch shipments

Revision ID: 225faeae24c5
Revises: aa5cf3f2056a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "225faeae24c5"
down_revision: str | Sequence[str] | None = "aa5cf3f2056a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PACKED = sa.text("state = 'packed'")
PACKED_OR_SHIPPED = sa.text("state IN ('packed', 'shipped')")
SHIPPED = sa.text("state = 'shipped'")
ITEM_NOT_VOIDED = sa.text("voided_at IS NULL")


def upgrade() -> None:
    """Create batch shipments and their items and add the shipped state of a KG unit."""
    op.drop_constraint(op.f("ck_kg_units_kg_state"), "kg_units", type_="check")
    op.create_check_constraint(
        op.f("ck_kg_units_kg_state"),
        "kg_units",
        "state IN ('registered', 'packed', 'shipped', 'scrapped')",
    )
    op.drop_constraint(op.f("ck_kg_units_packed_at_with_packed_state"), "kg_units", type_="check")
    op.create_check_constraint(
        op.f("ck_kg_units_packed_at_with_packed_state"),
        "kg_units",
        "(state IN ('packed', 'shipped')) = (packed_at IS NOT NULL)",
    )
    op.drop_index(op.f("ix_kg_units_packed_batch_id"), table_name="kg_units", postgresql_where=PACKED)
    op.create_index(op.f("ix_kg_units_packed_batch_id"), "kg_units", ["batch_id"], postgresql_where=PACKED_OR_SHIPPED)
    op.create_index(op.f("ix_kg_units_shipped_batch_id"), "kg_units", ["batch_id"], postgresql_where=SHIPPED)

    op.create_table(
        "batch_shipments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "completed",
                "voided",
                name="batch_shipment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("recipient", sa.String(length=256), nullable=True),
        sa.Column("waybill_number", sa.String(length=64), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(status = 'open' AND completed_at IS NULL) OR (status = 'completed' AND completed_at IS NOT NULL) "
            "OR status = 'voided'",
            name=op.f("ck_batch_shipments_completed_at_with_status"),
        ),
        sa.CheckConstraint(
            "(status = 'voided') = (voided_at IS NOT NULL)",
            name=op.f("ck_batch_shipments_voided_at_with_status"),
        ),
        sa.CheckConstraint(
            "(voided_at IS NULL) = (void_reason IS NULL)",
            name=op.f("ck_batch_shipments_void_reason_with_voided_at"),
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name=op.f("fk_batch_shipments_batch_id_batches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user_account.id"],
            name=op.f("fk_batch_shipments_created_by_id_user_account"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_batch_shipments")),
        sa.UniqueConstraint("number", name=op.f("uq_batch_shipments_number")),
    )
    op.create_index(
        op.f("ix_batch_shipments_batch_id_created_at"),
        "batch_shipments",
        ["batch_id", "created_at"],
    )
    op.create_index(op.f("ix_batch_shipments_created_by_id"), "batch_shipments", ["created_by_id"])

    op.create_table(
        "batch_shipment_items",
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("dev_eui", sa.String(length=16), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dev_eui"],
            ["kg_units.dev_eui"],
            name=op.f("fk_batch_shipment_items_dev_eui_kg_units"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["batch_shipments.id"],
            name=op.f("fk_batch_shipment_items_shipment_id_batch_shipments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("shipment_id", "dev_eui", name=op.f("pk_batch_shipment_items")),
    )
    op.create_index(
        op.f("ix_batch_shipment_items_shipment_id_created_at"),
        "batch_shipment_items",
        ["shipment_id", "created_at"],
    )
    op.create_index(
        op.f("uq_batch_shipment_items_dev_eui_not_voided"),
        "batch_shipment_items",
        ["dev_eui"],
        unique=True,
        postgresql_where=ITEM_NOT_VOIDED,
    )


def downgrade() -> None:
    """Drop batch shipments and the shipped state; fails while shipped KG units exist."""
    op.drop_index(
        op.f("uq_batch_shipment_items_dev_eui_not_voided"),
        table_name="batch_shipment_items",
        postgresql_where=ITEM_NOT_VOIDED,
    )
    op.drop_index(op.f("ix_batch_shipment_items_shipment_id_created_at"), table_name="batch_shipment_items")
    op.drop_table("batch_shipment_items")
    op.drop_index(op.f("ix_batch_shipments_created_by_id"), table_name="batch_shipments")
    op.drop_index(op.f("ix_batch_shipments_batch_id_created_at"), table_name="batch_shipments")
    op.drop_table("batch_shipments")

    op.drop_index(op.f("ix_kg_units_shipped_batch_id"), table_name="kg_units", postgresql_where=SHIPPED)
    op.drop_index(op.f("ix_kg_units_packed_batch_id"), table_name="kg_units", postgresql_where=PACKED_OR_SHIPPED)
    op.create_index(op.f("ix_kg_units_packed_batch_id"), "kg_units", ["batch_id"], postgresql_where=PACKED)
    op.drop_constraint(op.f("ck_kg_units_packed_at_with_packed_state"), "kg_units", type_="check")
    op.create_check_constraint(
        op.f("ck_kg_units_packed_at_with_packed_state"),
        "kg_units",
        "(state = 'packed') = (packed_at IS NOT NULL)",
    )
    op.drop_constraint(op.f("ck_kg_units_kg_state"), "kg_units", type_="check")
    op.create_check_constraint(
        op.f("ck_kg_units_kg_state"),
        "kg_units",
        "state IN ('registered', 'packed', 'scrapped')",
    )
