"""add users

Revision ID: 9afe278cb093
Revises: d72825436eb0
Create Date: 2026-09-23 09:47:55.428857+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Revision identifiers used by Alembic.
revision: str = "9afe278cb093"
down_revision: str | Sequence[str] | None = "d72825436eb0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create application users."""
    user_role = sa.Enum(
        "administrator",
        "manager",
        "engineer",
        "packer",
        "operator",
        name="user_role",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("identity_login", sa.String(length=255), nullable=False),
        sa.Column("identity_active", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_account"),
        sa.UniqueConstraint("identity_id", name="uq_user_account_identity_id"),
        comment="Application users associated with Kratos identities",
    )


def downgrade() -> None:
    """Drop application users."""
    op.drop_table("user_account")
