"""split KG state from verification status

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep only intrinsic KG state; OTK progress remains in verification sessions."""
    op.drop_index("ix_kg_units_status", table_name="kg_units")
    op.drop_constraint("kg_status", "kg_units", type_="check")
    op.alter_column("kg_units", "status", new_column_name="state")
    op.execute(
        "UPDATE kg_units SET state = 'REGISTERED' WHERE state NOT IN ('REGISTERED', 'SCRAPPED')"
    )
    op.create_check_constraint(
        "kg_state",
        "kg_units",
        "state IN ('REGISTERED', 'SCRAPPED')",
    )
    op.create_index("ix_kg_units_state", "kg_units", ["state"])


def downgrade() -> None:
    """Restore the former broad KG status column for rollback compatibility."""
    op.drop_index("ix_kg_units_state", table_name="kg_units")
    op.drop_constraint("kg_state", "kg_units", type_="check")
    op.alter_column("kg_units", "state", new_column_name="status")
    op.create_check_constraint(
        "kg_status",
        "kg_units",
        "status IN ('REGISTERED', 'TESTING', 'TEST_FAILED', 'IN_ENGINEER_REPAIR', "
        "'IN_PRODUCTION_REPAIR', 'READY_FOR_RETEST', 'READY_FOR_PACKING', 'PACKED', "
        "'SHIPPED', 'SCRAPPED')",
    )
    op.create_index("ix_kg_units_status", "kg_units", ["status"])
