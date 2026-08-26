"""expand audit actor snapshot

Revision ID: d42c9e7f1b35
Revises: f37a8d6c9e10
Create Date: 2026-08-20 13:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d42c9e7f1b35"
down_revision: str | Sequence[str] | None = "f37a8d6c9e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store generic actor display fields while preserving the previous backend."""
    op.alter_column(
        "audit_events",
        "actor_id",
        existing_type=sa.Uuid(),
        type_=sa.String(length=255),
        postgresql_using="actor_id::text",
    )
    op.add_column(
        "audit_events", sa.Column("actor_display_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "audit_events", sa.Column("actor_identifier", sa.String(length=255), nullable=True)
    )
    op.execute(
        """
        UPDATE audit_events
        SET
            actor_display_name = CASE
                WHEN actor_label ~ '^.* <[^<>]+>$'
                    THEN regexp_replace(actor_label, ' <[^<>]+>$', '')
                ELSE actor_label
            END,
            actor_identifier = CASE
                WHEN actor_label ~ '^.* <[^<>]+>$'
                    THEN substring(actor_label FROM ' <([^<>]+)>$')
                ELSE NULL
            END
        WHERE actor_label IS NOT NULL
        """
    )
    # Keep the expansion compatible with an older backend that only writes
    # actor_user_id. Newer backends write the actor snapshot directly.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_events_populate_actor() RETURNS trigger AS $$
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


def downgrade() -> None:
    """Restore UUID actor identifiers for the previous audit representation."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_events_populate_actor() RETURNS trigger AS $$
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
    op.drop_column("audit_events", "actor_identifier")
    op.drop_column("audit_events", "actor_display_name")
    op.alter_column(
        "audit_events",
        "actor_id",
        existing_type=sa.String(length=255),
        type_=sa.Uuid(),
        postgresql_using=(
            "CASE WHEN actor_id ~ "
            "'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            "[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' "
            "THEN actor_id::uuid ELSE NULL END"
        ),
    )
