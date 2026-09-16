"""init

Revision ID: d72825436eb0
Revises:
Create Date: 2026-09-16 16:48:02.538552+00:00

"""

from collections.abc import Sequence

# Revision identifiers used by Alembic.
revision: str = "d72825436eb0"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the schema changes for this revision."""
    pass


def downgrade() -> None:
    """Revert the schema changes for this revision."""
    pass
