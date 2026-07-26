"""initial migration

Revision ID: 61e9513b714a
Revises:
Create Date: 2026-07-13 11:45:03.258193+00:00

"""

from collections.abc import Sequence

# Revision identifiers used by Alembic.
revision: str = '61e9513b714a'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	"""Apply the schema changes for this revision."""
	pass


def downgrade() -> None:
	"""Revert the schema changes for this revision."""
	pass
