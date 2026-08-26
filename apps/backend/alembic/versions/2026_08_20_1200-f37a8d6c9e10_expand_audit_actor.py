"""expand audit actor representation

Revision ID: f37a8d6c9e10
Revises: a4e7b91c2d5f
Create Date: 2026-08-20 12:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f37a8d6c9e10"
down_revision: str | Sequence[str] | None = "a4e7b91c2d5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the polymorphic actor snapshot without breaking the prior backend."""
    op.add_column("audit_events", sa.Column("actor_type", sa.String(length=64), nullable=True))
    op.add_column("audit_events", sa.Column("actor_id", sa.Uuid(), nullable=True))
    op.add_column("audit_events", sa.Column("actor_label", sa.String(length=255), nullable=True))

    op.execute(
        """
        UPDATE audit_events
        SET
            actor_type = CASE WHEN actor_user_id IS NULL THEN 'system' ELSE 'user' END,
            actor_id = actor_user_id
        """
    )
    # The trigger allows a still-running previous backend, which only writes
    # actor_user_id, to coexist with this expand migration.
    op.execute(
        """
        CREATE FUNCTION audit_events_populate_actor() RETURNS trigger AS $$
        BEGIN
            IF NEW.actor_type IS NULL THEN
                NEW.actor_type := CASE
                    WHEN NEW.actor_user_id IS NULL THEN 'system'
                    ELSE 'user'
                END;
            END IF;
            IF NEW.actor_id IS NULL AND NEW.actor_user_id IS NOT NULL THEN
                NEW.actor_id := NEW.actor_user_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_events_populate_actor
        BEFORE INSERT OR UPDATE OF actor_user_id ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_populate_actor();
        """
    )
    op.alter_column("audit_events", "actor_type", nullable=False)
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_type", "actor_id"])


def downgrade() -> None:
    """Remove the expanded representation while retaining the legacy actor reference."""
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.execute("DROP TRIGGER trg_audit_events_populate_actor ON audit_events")
    op.execute("DROP FUNCTION audit_events_populate_actor()")
    op.drop_column("audit_events", "actor_label")
    op.drop_column("audit_events", "actor_id")
    op.drop_column("audit_events", "actor_type")
