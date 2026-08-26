"""contract identity state to active and inactive

Revision ID: a92b6c3d4e5f
Revises: e61f4b8a9c72
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a92b6c3d4e5f"
down_revision: str | Sequence[str] | None = "e61f4b8a9c72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE users SET identity_state = 'inactive' WHERE identity_state = 'missing'")
    op.alter_column(
        "users",
        "identity_state",
        existing_type=sa.String(length=16),
        server_default="inactive",
    )
    op.create_check_constraint(
        "ck_users_identity_state_allowed_values",
        "users",
        "identity_state IN ('active', 'inactive')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_identity_state_allowed_values", "users", type_="check")
    op.alter_column(
        "users",
        "identity_state",
        existing_type=sa.String(length=16),
        server_default="missing",
    )
