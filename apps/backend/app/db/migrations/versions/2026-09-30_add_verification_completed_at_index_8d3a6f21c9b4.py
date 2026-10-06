"""add verification completed at index

Revision ID: 8d3a6f21c9b4
Revises: 5c1e8b7d2f40
"""

from collections.abc import Sequence

from alembic import op

revision: str = "8d3a6f21c9b4"
down_revision: str | Sequence[str] | None = "5c1e8b7d2f40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Index the sessions of a PAK by when they finished, for the state of its slots."""
    op.create_index(
        "ix_verification_sessions_pak_id_completed_at",
        "verification_sessions",
        ["pak_id", "completed_at"],
    )


def downgrade() -> None:
    """Drop the index."""
    op.drop_index("ix_verification_sessions_pak_id_completed_at", table_name="verification_sessions")
