"""Add optimistic versioning for user reconciliation.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""

import sqlalchemy as sa

from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1")
    )


def downgrade() -> None:
    op.drop_column("users", "version")
