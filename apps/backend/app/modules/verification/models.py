from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class VerificationSessionStatus(StrEnum):
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    INCOMPLETE = "INCOMPLETE"


VERIFICATION_SESSION_STATUS_DB_TYPE = Enum(
    VerificationSessionStatus,
    name="verification_session_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [status.value for status in enum_type],
)


class VerificationStepStatus(StrEnum):
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


VERIFICATION_STEP_STATUS_DB_TYPE = Enum(
    VerificationStepStatus,
    name="verification_step_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [status.value for status in enum_type],
)


class VerificationSession(Base):
    __tablename__ = "verification_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    kg_dev_eui: Mapped[str] = mapped_column(
        String(16),
        ForeignKey(
            "kg_units.dev_eui",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    firmware_version: Mapped[str] = mapped_column(String(64), nullable=False)
    pak_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "pak_devices.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    slot_no: Mapped[int] = mapped_column(Integer, nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VerificationSessionStatus] = mapped_column(
        VERIFICATION_SESSION_STATUS_DB_TYPE,
        nullable=False,
        default=VerificationSessionStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "slot_no > 0",
            name="verification_session_slot_no_positive",
        ),
        CheckConstraint(
            "total_steps > 0",
            name="verification_session_total_steps_positive",
        ),
        Index(
            "ix_verification_sessions_kg_started_at",
            "kg_dev_eui",
            "started_at",
        ),
        Index(
            "ix_verification_sessions_pak_started_at",
            "pak_id",
            "started_at",
        ),
        Index(
            "ix_verification_sessions_status_last_activity_at",
            "status",
            "last_activity_at",
        ),
        Index(
            "ux_verification_running_by_kg",
            "kg_dev_eui",
            unique=True,
            postgresql_where=text(
                "status = 'RUNNING'"
            ),
        ),
        Index(
            "ux_verification_running_by_pak_slot",
            "pak_id",
            "slot_no",
            unique=True,
            postgresql_where=text(
                "status = 'RUNNING'"
            ),
        ),
    )


class VerificationStep(Base):
    __tablename__ = "verification_steps"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "verification_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    pak_test_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "pak_tests.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    defect_group_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "defect_groups.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    test_name: Mapped[str] = mapped_column(String(128), nullable=False)
    test_label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[VerificationStepStatus] = mapped_column(
        VERIFICATION_STEP_STATUS_DB_TYPE,
        nullable=False,
        default=VerificationStepStatus.RUNNING,
    )
    measurement_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_group_code: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "step_no > 0",
            name="verification_step_no_positive",
        ),
        CheckConstraint(
            """
            measurement_min_value IS NULL
            OR measurement_max_value IS NULL
            OR measurement_min_value <= measurement_max_value
            """,
            name="verification_step_measurement_range_valid",
        ),
        UniqueConstraint(
            "session_id",
            "step_no",
            name="uq_verification_steps_session_step_no",
        ),
        Index(
            "ix_verification_steps_test_name",
            "test_name",
        ),
        Index(
            "ix_verification_steps_status",
            "status",
        ),
    )
