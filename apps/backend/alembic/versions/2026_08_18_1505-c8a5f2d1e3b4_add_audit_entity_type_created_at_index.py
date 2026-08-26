"""add audit entity type and created at index

Revision ID: c8a5f2d1e3b4
Revises: 8f2c7ddf1a31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c8a5f2d1e3b4"
down_revision: str | Sequence[str] | None = "8f2c7ddf1a31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_audit_events_entity_type_created_at "
        "ON audit_events (entity_type, created_at DESC)"
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity_type_created_at", table_name="audit_events")
