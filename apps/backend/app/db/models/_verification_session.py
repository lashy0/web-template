from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.enums import PakDeviceKind, VerificationSessionStatus, enum_values
from app.db.models._pak_device import PakDevice
from app.db.models._verification_step import VerificationStep


class VerificationSession(UUIDv7AuditBase):
    """One run of the checks of a PAK slot on one KG unit.

    A KG unit and a PAK slot each have at most one running session.
    """

    __tablename__ = "verification_sessions"

    dev_eui: Mapped[str] = mapped_column(
        ForeignKey("kg_units.dev_eui", ondelete="RESTRICT"),
        nullable=False,
    )

    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    """The batch of the KG unit, which never changes; kept to filter sessions by batch."""

    pak_id: Mapped[UUID] = mapped_column(
        ForeignKey("pak_devices.id", ondelete="RESTRICT"),
        nullable=False,
    )

    pak_kind: Mapped[PakDeviceKind] = mapped_column(
        Enum(
            PakDeviceKind,
            name="pak_device_kind",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    """The PAK's kind when the session started; only ``otk_line`` sessions set the KG OTK status."""

    slot_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    firmware_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    total_steps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[VerificationSessionStatus] = mapped_column(
        Enum(
            VerificationSessionStatus,
            name="verification_session_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=VerificationSessionStatus.RUNNING,
    )

    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    pak: Mapped[PakDevice] = relationship(lazy="selectin")
    steps: Mapped[list[VerificationStep]] = relationship(
        lazy="raise",
        order_by=VerificationStep.step_no,
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("slot_no > 0", name="slot_no_positive"),
        CheckConstraint("total_steps > 0", name="total_steps_positive"),
        CheckConstraint("(status = 'running') = (completed_at IS NULL)", name="completed_at_when_finished"),
        Index("ix_verification_sessions_dev_eui_started_at", "dev_eui", "started_at"),
        Index("ix_verification_sessions_batch_id_started_at", "batch_id", "started_at"),
        Index("ix_verification_sessions_pak_id_started_at", "pak_id", "started_at"),
        Index("ix_verification_sessions_started_at", "started_at"),
        Index(
            "ix_verification_sessions_running_last_activity_at",
            "last_activity_at",
            postgresql_where=text("status = 'running'"),
        ),
        Index(
            "ux_verification_sessions_running_dev_eui",
            "dev_eui",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
        Index(
            "ux_verification_sessions_running_pak_slot",
            "pak_id",
            "slot_no",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
    )
