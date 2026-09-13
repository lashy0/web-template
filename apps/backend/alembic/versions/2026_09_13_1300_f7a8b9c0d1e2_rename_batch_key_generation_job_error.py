"""store batch key generation failure as an error code

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "batch_key_generation_jobs",
        "error",
        new_column_name="error_code",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.execute(
        """
        UPDATE batch_key_generation_jobs
        SET error_code = 'batch_key_generation_failed'
        WHERE error_code IS NOT NULL
        """
    )


def downgrade() -> None:
    op.alter_column(
        "batch_key_generation_jobs",
        "error_code",
        new_column_name="error",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
