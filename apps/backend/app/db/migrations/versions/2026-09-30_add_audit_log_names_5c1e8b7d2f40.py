"""add audit log names

Revision ID: 5c1e8b7d2f40
Revises: 225faeae24c5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c1e8b7d2f40"
down_revision: str | Sequence[str] | None = "225faeae24c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Target types named apart from their label, and the tables of their records.
NAMED_TARGET_TABLES = {
    "user": "user_account",
    "kg_version": "kg_versions",
    "kg_prefix": "kg_prefixes",
    "defect_group": "defect_groups",
    "defect_type": "defect_types",
}


def upgrade() -> None:
    """Add the actor and target names and fill them in from the current records."""
    op.add_column("audit_log", sa.Column("actor_name", sa.String(length=255), nullable=True))
    op.add_column("audit_log", sa.Column("target_name", sa.String(length=255), nullable=True))

    # Earlier entries get today's names: the names at the time were never recorded.
    op.execute(
        "UPDATE audit_log SET actor_name = user_account.name FROM user_account WHERE audit_log.actor_id = user_account.id"
    )
    for target_type, table in NAMED_TARGET_TABLES.items():
        op.execute(
            f"UPDATE audit_log SET target_name = {table}.name FROM {table} "  # noqa: S608 - constant table names
            f"WHERE audit_log.target_type = '{target_type}' AND audit_log.target_id = {table}.id::text"
        )


def downgrade() -> None:
    """Drop the actor and target names."""
    op.drop_column("audit_log", "target_name")
    op.drop_column("audit_log", "actor_name")
