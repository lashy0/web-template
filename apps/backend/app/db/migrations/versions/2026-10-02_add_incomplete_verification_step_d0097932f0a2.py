"""add incomplete verification step status

Revision ID: d0097932f0a2
Revises: 8d3a6f21c9b4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0097932f0a2"
down_revision: str | Sequence[str] | None = "8d3a6f21c9b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = "ck_verification_steps_verification_step_status"


def upgrade() -> None:
    """Mark the steps the system closed with their session as incomplete instead of aborted."""
    op.drop_constraint(op.f(CONSTRAINT), "verification_steps", type_="check")
    op.alter_column("verification_steps", "status", existing_type=sa.String(7), type_=sa.String(10))
    op.create_check_constraint(
        op.f(CONSTRAINT),
        "verification_steps",
        "status IN ('running', 'passed', 'failed', 'aborted', 'incomplete')",
    )
    # A PAK reports only passed or failed steps; an aborted step of an
    # incomplete session was closed by the system, never by the PAK.
    op.execute(
        "UPDATE verification_steps SET status = 'incomplete' "
        "WHERE status = 'aborted' AND session_id IN "
        "(SELECT id FROM verification_sessions WHERE status = 'incomplete')"
    )


def downgrade() -> None:
    """Return incomplete steps to aborted and restore the previous statuses."""
    op.execute("UPDATE verification_steps SET status = 'aborted' WHERE status = 'incomplete'")
    op.drop_constraint(op.f(CONSTRAINT), "verification_steps", type_="check")
    op.alter_column("verification_steps", "status", existing_type=sa.String(10), type_=sa.String(7))
    op.create_check_constraint(
        op.f(CONSTRAINT),
        "verification_steps",
        "status IN ('running', 'passed', 'failed', 'aborted')",
    )
