"""add verification sessions and steps

Revision ID: c3d4e5f6a7b8
Revises: a7b8c9d0e1f2
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create PAK verification session and step storage."""
    verification_session_status = sa.Enum(
        "RUNNING",
        "PASSED",
        "FAILED",
        "ABORTED",
        "INCOMPLETE",
        name="verification_session_status",
        native_enum=False,
        create_constraint=True,
    )
    verification_step_status = sa.Enum(
        "RUNNING",
        "PASSED",
        "FAILED",
        "ABORTED",
        name="verification_step_status",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "verification_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kg_dev_eui", sa.String(length=16), nullable=False),
        sa.Column("firmware_version", sa.String(length=64), nullable=False),
        sa.Column("pak_id", sa.Uuid(), nullable=False),
        sa.Column("slot_no", sa.Integer(), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("status", verification_session_status, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("slot_no > 0", name="verification_session_slot_no_positive"),
        sa.CheckConstraint("total_steps > 0", name="verification_session_total_steps_positive"),
        sa.ForeignKeyConstraint(
            ["kg_dev_eui"],
            ["kg_units.dev_eui"],
            name="fk_verification_sessions_kg_dev_eui_kg_units",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pak_id"],
            ["pak_devices.id"],
            name="fk_verification_sessions_pak_id_pak_devices",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_sessions"),
    )
    op.create_index(
        "ix_verification_sessions_kg_started_at",
        "verification_sessions",
        ["kg_dev_eui", "started_at"],
    )
    op.create_index(
        "ix_verification_sessions_pak_started_at",
        "verification_sessions",
        ["pak_id", "started_at"],
    )
    op.create_index(
        "ix_verification_sessions_status_last_activity_at",
        "verification_sessions",
        ["status", "last_activity_at"],
    )
    op.create_index(
        "ux_verification_running_by_kg",
        "verification_sessions",
        ["kg_dev_eui"],
        unique=True,
        postgresql_where=sa.text("status = 'RUNNING'"),
    )
    op.create_index(
        "ux_verification_running_by_pak_slot",
        "verification_sessions",
        ["pak_id", "slot_no"],
        unique=True,
        postgresql_where=sa.text("status = 'RUNNING'"),
    )

    op.create_table(
        "verification_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("test_name", sa.String(length=128), nullable=False),
        sa.Column("test_label", sa.String(length=255), nullable=True),
        sa.Column("status", verification_step_status, nullable=False),
        sa.Column("measurement_value", sa.Float(), nullable=True),
        sa.Column("measurement_min_value", sa.Float(), nullable=True),
        sa.Column("measurement_max_value", sa.Float(), nullable=True),
        sa.Column("measurement_unit", sa.String(length=32), nullable=True),
        sa.Column("error_group_code", sa.String(length=32), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("step_no > 0", name="verification_step_no_positive"),
        sa.CheckConstraint(
            """
            measurement_min_value IS NULL
            OR measurement_max_value IS NULL
            OR measurement_min_value <= measurement_max_value
            """,
            name="verification_step_measurement_range_valid",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["verification_sessions.id"],
            name="fk_verification_steps_session_id_verification_sessions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_steps"),
        sa.UniqueConstraint("session_id", "step_no", name="uq_verification_steps_session_step_no"),
    )
    op.create_index("ix_verification_steps_test_name", "verification_steps", ["test_name"])
    op.create_index("ix_verification_steps_status", "verification_steps", ["status"])


def downgrade() -> None:
    """Remove PAK verification session and step storage."""
    op.drop_index("ix_verification_steps_status", table_name="verification_steps")
    op.drop_index("ix_verification_steps_test_name", table_name="verification_steps")
    op.drop_table("verification_steps")

    op.drop_index("ux_verification_running_by_pak_slot", table_name="verification_sessions")
    op.drop_index("ux_verification_running_by_kg", table_name="verification_sessions")
    op.drop_index(
        "ix_verification_sessions_status_last_activity_at",
        table_name="verification_sessions",
    )
    op.drop_index("ix_verification_sessions_pak_started_at", table_name="verification_sessions")
    op.drop_index("ix_verification_sessions_kg_started_at", table_name="verification_sessions")
    op.drop_table("verification_sessions")
