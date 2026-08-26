"""rename identity state to auth state

Revision ID: b3c4d5e6f7a8
Revises: a92b6c3d4e5f
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | Sequence[str] | None = "a92b6c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_users_identity_state_allowed_values", "users", type_="check")
    op.drop_index("ix_users_identity_state", table_name="users")
    op.alter_column("users", "identity_state", new_column_name="auth_state")
    op.alter_column(
        "users",
        "identity_state_synced_at",
        new_column_name="auth_state_synced_at",
        existing_type=sa.DateTime(timezone=True),
    )
    op.create_check_constraint(
        "ck_users_auth_state_allowed_values",
        "users",
        "auth_state IN ('active', 'inactive')",
    )
    op.create_index("ix_users_auth_state", "users", ["auth_state"])


def downgrade() -> None:
    op.drop_constraint("ck_users_auth_state_allowed_values", "users", type_="check")
    op.drop_index("ix_users_auth_state", table_name="users")
    op.alter_column("users", "auth_state", new_column_name="identity_state")
    op.alter_column(
        "users",
        "auth_state_synced_at",
        new_column_name="identity_state_synced_at",
        existing_type=sa.DateTime(timezone=True),
    )
    op.create_check_constraint(
        "ck_users_identity_state_allowed_values",
        "users",
        "identity_state IN ('active', 'inactive')",
    )
    op.create_index("ix_users_identity_state", "users", ["identity_state"])
