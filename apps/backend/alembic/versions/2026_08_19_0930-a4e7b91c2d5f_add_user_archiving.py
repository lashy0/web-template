"""add user archiving

Revision ID: a4e7b91c2d5f
Revises: c8a5f2d1e3b4
Create Date: 2026-08-19 09:30:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4e7b91c2d5f"
down_revision: str | Sequence[str] | None = "c8a5f2d1e3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_archived_at", "users", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_users_archived_at", table_name="users")
    op.drop_column("users", "archived_at")
