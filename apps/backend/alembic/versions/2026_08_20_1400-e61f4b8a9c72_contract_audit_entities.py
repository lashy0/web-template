"""contract audit entity snapshots

Revision ID: e61f4b8a9c72
Revises: d42c9e7f1b35
Create Date: 2026-08-20 14:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e61f4b8a9c72"
down_revision: str | Sequence[str] | None = "d42c9e7f1b35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store entity snapshots and remove the legacy actor reference."""
    op.add_column(
        "audit_events", sa.Column("entity_display_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "audit_events", sa.Column("entity_identifier", sa.String(length=255), nullable=True)
    )
    op.execute(
        """
        UPDATE audit_events
        SET
            entity_display_name = COALESCE(new_data->>'name', old_data->>'name'),
            entity_identifier = COALESCE(new_data->>'login', old_data->>'login')
        WHERE entity_type = 'user'
        """
    )
    op.execute("DROP TRIGGER trg_audit_events_populate_actor ON audit_events")
    op.execute("DROP FUNCTION audit_events_populate_actor()")
    op.drop_constraint(op.f("fk_audit_events_actor_user_id_users"), "audit_events", type_="foreignkey")
    op.drop_index(op.f("ix_audit_events_actor_user_id"), table_name="audit_events")
    op.drop_column("audit_events", "actor_user_id")


def downgrade() -> None:
    """Restore the legacy actor reference for the previous backend."""
    op.add_column("audit_events", sa.Column("actor_user_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE audit_events
        SET actor_user_id = CASE
            WHEN actor_type = 'user'
                AND actor_id ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
            THEN actor_id::uuid
            ELSE NULL
        END
        """
    )
    op.create_foreign_key(
        op.f("fk_audit_events_actor_user_id_users"),
        "audit_events",
        "users",
        ["actor_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_audit_events_actor_user_id"), "audit_events", ["actor_user_id"], unique=False
    )
    op.execute(
        """
        CREATE FUNCTION audit_events_populate_actor() RETURNS trigger AS $$
        DECLARE
            legacy_name text;
            legacy_login text;
        BEGIN
            IF NEW.actor_type IS NULL THEN
                NEW.actor_type := CASE
                    WHEN NEW.actor_user_id IS NULL THEN 'system'
                    ELSE 'user'
                END;
            END IF;
            IF NEW.actor_id IS NULL AND NEW.actor_user_id IS NOT NULL THEN
                NEW.actor_id := NEW.actor_user_id::text;
            END IF;
            IF NEW.actor_user_id IS NOT NULL
                AND (NEW.actor_display_name IS NULL OR NEW.actor_identifier IS NULL) THEN
                SELECT name, identity_login
                INTO legacy_name, legacy_login
                FROM users
                WHERE id = NEW.actor_user_id;
                NEW.actor_display_name := COALESCE(NEW.actor_display_name, legacy_name);
                NEW.actor_identifier := COALESCE(NEW.actor_identifier, legacy_login);
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
    op.drop_column("audit_events", "entity_identifier")
    op.drop_column("audit_events", "entity_display_name")
