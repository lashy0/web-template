"""add asynchronous batch preparation state

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "batch_key_generation_jobs",
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="CREATING"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("batch_id"),
        sa.CheckConstraint(
            "status IN ('CREATING', 'GENERATING', 'READY', 'FAILED', 'CANCELLING')",
            name="batch_key_generation_job_status",
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="batch_key_generation_job_progress_range",
        ),
    )
    op.create_index(
        "ix_batch_key_generation_jobs_status", "batch_key_generation_jobs", ["status"]
    )

    op.execute(
        """
        INSERT INTO batch_key_generation_jobs (batch_id, status, progress)
        SELECT id,
            CASE key_generation_status
                WHEN 'PENDING' THEN 'CREATING'
                WHEN 'RUNNING' THEN 'GENERATING'
                WHEN 'COMPLETED' THEN 'READY'
                WHEN 'FAILED' THEN 'FAILED'
            END,
            CASE key_generation_status
                WHEN 'COMPLETED' THEN 100
                ELSE 0
            END
        FROM batches
        """
    )
    op.drop_constraint("batch_key_generation_status", "batches", type_="check")
    op.drop_column("batches", "key_generation_status")


def downgrade() -> None:
    op.add_column(
        "batches",
        sa.Column(
            "key_generation_status",
            sa.String(length=9),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.create_check_constraint(
        "batch_key_generation_status",
        "batches",
        "key_generation_status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
    )
    op.drop_index(
        "ix_batch_key_generation_jobs_status",
        table_name="batch_key_generation_jobs",
    )
    op.drop_table("batch_key_generation_jobs")
