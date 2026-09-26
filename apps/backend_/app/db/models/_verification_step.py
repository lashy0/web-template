from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.enums import VerificationStepStatus, enum_values


class VerificationStep(UUIDv7AuditBase):
    """One check of a verification session, as the PAK reported it.

    The check's name, label and defect group code are copied from the report,
    so the history stays as it was when the catalog changes.
    """

    __tablename__ = "verification_steps"

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("verification_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    step_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    check_id: Mapped[UUID] = mapped_column(
        ForeignKey("pak_checks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    check_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    check_label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    defect_group_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    defect_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("defect_groups.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    """The active group with ``defect_group_code`` when the step started, if there was one."""

    status: Mapped[VerificationStepStatus] = mapped_column(
        Enum(
            VerificationStepStatus,
            name="verification_step_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=VerificationStepStatus.RUNNING,
    )

    measurement_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    measurement_min: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    measurement_max: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    measurement_unit: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("step_no > 0", name="step_no_positive"),
        CheckConstraint(
            "measurement_min IS NULL OR measurement_max IS NULL OR measurement_min <= measurement_max",
            name="measurement_range",
        ),
        CheckConstraint("(status = 'running') = (completed_at IS NULL)", name="completed_at_when_finished"),
        UniqueConstraint("session_id", "step_no", name="uq_verification_steps_session_id_step_no"),
    )
