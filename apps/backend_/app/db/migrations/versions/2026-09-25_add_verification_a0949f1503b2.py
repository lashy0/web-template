"""add PAK checks, verification sessions and KG OTK status

Revision ID: a0949f1503b2
Revises: c71e4b9d2a05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0949f1503b2"
down_revision: str | Sequence[str] | None = "c71e4b9d2a05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUNNING = sa.text("status = 'running'")


def upgrade() -> None:
    """Create the check catalog and verification history; every KG unit starts not verified."""
    pak_device_kind = sa.Enum(
        "engineering",
        "otk_line",
        name="pak_device_kind",
        native_enum=False,
        create_constraint=True,
    )
    session_status = sa.Enum(
        "running",
        "passed",
        "failed",
        "aborted",
        "incomplete",
        name="verification_session_status",
        native_enum=False,
        create_constraint=True,
    )
    step_status = sa.Enum(
        "running",
        "passed",
        "failed",
        "aborted",
        name="verification_step_status",
        native_enum=False,
        create_constraint=True,
    )
    kg_otk_status = sa.Enum(
        "not_verified",
        "passed",
        "failed",
        name="kg_otk_status",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "pak_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("defect_group_code", sa.String(length=32), nullable=False),
        sa.Column("defect_group_id", sa.Uuid(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["defect_group_id"],
            ["defect_groups.id"],
            name="fk_pak_checks_defect_group_id_defect_groups",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pak_checks"),
        sa.UniqueConstraint("name", "label", name="uq_pak_checks_name_label"),
    )
    op.create_index("ix_pak_checks_defect_group_id", "pak_checks", ["defect_group_id"])

    op.create_table(
        "verification_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dev_eui", sa.String(length=16), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("pak_id", sa.Uuid(), nullable=False),
        sa.Column("pak_kind", pak_device_kind, nullable=False),
        sa.Column("slot_no", sa.Integer(), nullable=False),
        sa.Column("firmware_version", sa.String(length=64), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("status", session_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("slot_no > 0", name=op.f("ck_verification_sessions_slot_no_positive")),
        sa.CheckConstraint("total_steps > 0", name=op.f("ck_verification_sessions_total_steps_positive")),
        sa.CheckConstraint(
            "(status = 'running') = (completed_at IS NULL)",
            name=op.f("ck_verification_sessions_completed_at_when_finished"),
        ),
        sa.ForeignKeyConstraint(
            ["dev_eui"],
            ["kg_units.dev_eui"],
            name="fk_verification_sessions_dev_eui_kg_units",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name="fk_verification_sessions_batch_id_batches",
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
        "ix_verification_sessions_dev_eui_started_at",
        "verification_sessions",
        ["dev_eui", "started_at"],
    )
    op.create_index(
        "ix_verification_sessions_batch_id_started_at",
        "verification_sessions",
        ["batch_id", "started_at"],
    )
    op.create_index(
        "ix_verification_sessions_pak_id_started_at",
        "verification_sessions",
        ["pak_id", "started_at"],
    )
    op.create_index("ix_verification_sessions_started_at", "verification_sessions", ["started_at"])
    op.create_index(
        "ix_verification_sessions_running_last_activity_at",
        "verification_sessions",
        ["last_activity_at"],
        postgresql_where=RUNNING,
    )
    op.create_index(
        "ux_verification_sessions_running_dev_eui",
        "verification_sessions",
        ["dev_eui"],
        unique=True,
        postgresql_where=RUNNING,
    )
    op.create_index(
        "ux_verification_sessions_running_pak_slot",
        "verification_sessions",
        ["pak_id", "slot_no"],
        unique=True,
        postgresql_where=RUNNING,
    )

    op.create_table(
        "verification_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("check_id", sa.Uuid(), nullable=False),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("check_label", sa.String(length=255), nullable=False),
        sa.Column("defect_group_code", sa.String(length=32), nullable=False),
        sa.Column("defect_group_id", sa.Uuid(), nullable=True),
        sa.Column("status", step_status, nullable=False),
        sa.Column("measurement_value", sa.Float(), nullable=True),
        sa.Column("measurement_min", sa.Float(), nullable=True),
        sa.Column("measurement_max", sa.Float(), nullable=True),
        sa.Column("measurement_unit", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("step_no > 0", name=op.f("ck_verification_steps_step_no_positive")),
        sa.CheckConstraint(
            "measurement_min IS NULL OR measurement_max IS NULL OR measurement_min <= measurement_max",
            name=op.f("ck_verification_steps_measurement_range"),
        ),
        sa.CheckConstraint(
            "(status = 'running') = (completed_at IS NULL)",
            name=op.f("ck_verification_steps_completed_at_when_finished"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["verification_sessions.id"],
            name="fk_verification_steps_session_id_verification_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["pak_checks.id"],
            name="fk_verification_steps_check_id_pak_checks",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["defect_group_id"],
            ["defect_groups.id"],
            name="fk_verification_steps_defect_group_id_defect_groups",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_steps"),
        sa.UniqueConstraint("session_id", "step_no", name="uq_verification_steps_session_id_step_no"),
    )
    op.create_index("ix_verification_steps_check_id", "verification_steps", ["check_id"])
    op.create_index("ix_verification_steps_defect_group_id", "verification_steps", ["defect_group_id"])

    op.add_column(
        "kg_units",
        sa.Column("otk_status", kg_otk_status, server_default="not_verified", nullable=False),
    )
    op.add_column("kg_units", sa.Column("last_verification_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_kg_units_otk_status", "kg_units", ["otk_status"])


def downgrade() -> None:
    """Drop the verification history, the check catalog and the KG OTK status."""
    op.drop_index("ix_kg_units_otk_status", table_name="kg_units")
    op.drop_column("kg_units", "last_verification_at")
    op.drop_column("kg_units", "otk_status")
    op.drop_index("ix_verification_steps_defect_group_id", table_name="verification_steps")
    op.drop_index("ix_verification_steps_check_id", table_name="verification_steps")
    op.drop_table("verification_steps")
    op.drop_index("ux_verification_sessions_running_pak_slot", table_name="verification_sessions")
    op.drop_index("ux_verification_sessions_running_dev_eui", table_name="verification_sessions")
    op.drop_index("ix_verification_sessions_running_last_activity_at", table_name="verification_sessions")
    op.drop_index("ix_verification_sessions_started_at", table_name="verification_sessions")
    op.drop_index("ix_verification_sessions_pak_id_started_at", table_name="verification_sessions")
    op.drop_index("ix_verification_sessions_batch_id_started_at", table_name="verification_sessions")
    op.drop_index("ix_verification_sessions_dev_eui_started_at", table_name="verification_sessions")
    op.drop_table("verification_sessions")
    op.drop_index("ix_pak_checks_defect_group_id", table_name="pak_checks")
    op.drop_table("pak_checks")
