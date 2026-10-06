"""record who adds, ships and voids shipment units, drop shipment recipient and waybill

Revision ID: 3f6b9d2e7a15
Revises: 7183dcae0a44
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f6b9d2e7a15"
down_revision: str | Sequence[str] | None = "7183dcae0a44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_USER_COLUMNS = (
    ("batch_shipment_items", "added_by_id"),
    ("batch_shipments", "completed_by_id"),
    ("batch_shipments", "voided_by_id"),
)


def upgrade() -> None:
    """Earlier units and shipments keep no author; shipments lose their recipient and waybill number."""
    for table, column in _USER_COLUMNS:
        op.add_column(table, sa.Column(column, sa.Uuid(), nullable=True))
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column])
        op.create_foreign_key(
            op.f(f"fk_{table}_{column}_user_account"),
            table,
            "user_account",
            [column],
            ["id"],
            ondelete="SET NULL",
        )

    op.drop_column("batch_shipments", "recipient")
    op.drop_column("batch_shipments", "waybill_number")


def downgrade() -> None:
    op.add_column("batch_shipments", sa.Column("waybill_number", sa.String(length=64), nullable=True))
    op.add_column("batch_shipments", sa.Column("recipient", sa.String(length=256), nullable=True))

    for table, column in reversed(_USER_COLUMNS):
        op.drop_constraint(op.f(f"fk_{table}_{column}_user_account"), table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_column(table, column)
