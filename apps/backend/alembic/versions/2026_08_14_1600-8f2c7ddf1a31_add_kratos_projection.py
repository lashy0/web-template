"""add Kratos identity projection

Revision ID: 8f2c7ddf1a31
Revises: 84873fea28b1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8f2c7ddf1a31"
down_revision: str | Sequence[str] | None = "84873fea28b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.add_column("users", sa.Column("identity_login", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column("identity_state", sa.String(length=16), server_default="missing", nullable=False),
    )
    op.add_column("users", sa.Column("identity_state_synced_at", sa.DateTime(timezone=True)))
    op.create_index("ix_users_identity_state", "users", ["identity_state"])
    op.create_index("ix_users_identity_login", "users", ["identity_login"])
    op.execute(
        "CREATE INDEX ix_users_identity_login_trgm ON users USING gin (identity_login gin_trgm_ops)"
    )
    op.execute("CREATE INDEX ix_users_name_trgm ON users USING gin (name gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX ix_users_name_trgm")
    op.execute("DROP INDEX ix_users_identity_login_trgm")
    op.drop_index("ix_users_identity_login", table_name="users")
    op.drop_index("ix_users_identity_state", table_name="users")
    op.drop_column("users", "identity_state_synced_at")
    op.drop_column("users", "identity_state")
    op.drop_column("users", "identity_login")
