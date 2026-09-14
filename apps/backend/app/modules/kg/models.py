from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.contexts.production.kg.model import KgDevEuiPrefix, KgVersion
from app.infrastructure.database.base import Base

__all__ = ["KgDevEuiPrefix", "KgVersion"]

if TYPE_CHECKING:
    from app.modules.batch.models import Batch
    from app.modules.verification.models import VerificationSession


class KgState(StrEnum):
    REGISTERED = "REGISTERED"
    SCRAPPED = "SCRAPPED"


KG_STATE_DB_TYPE = Enum(
    KgState,
    name="kg_state",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [status.value for status in enum_type],
)


class KgUnit(Base):
    __tablename__ = "kg_units"

    dev_eui: Mapped[str] = mapped_column(String(16), primary_key=True)
    batch: Mapped["Batch"] = relationship(lazy="selectin")
    short_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id"),
        nullable=False,
    )
    state: Mapped[KgState] = mapped_column(
        KG_STATE_DB_TYPE,
        nullable=False,
        default=KgState.REGISTERED,
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
    lorawan_credentials: Mapped["LoRaWanCredentials | None"] = relationship(
        back_populates="kg_unit",
        uselist=False,
        lazy="noload",
        cascade="all, delete-orphan",
    )
    verification_sessions: Mapped[list["VerificationSession"]] = relationship(
        back_populates="kg_unit",
        lazy="noload",
    )

    __table_args__ = (
        CheckConstraint(
            "dev_eui ~ '^[0-9a-f]{16}$'",
            name="dev_eui_format",
        ),
        Index("ix_kg_units_batch_id", "batch_id"),
        Index("ix_kg_units_state", "state"),
    )


class LoRaWanCredentials(Base):
    __tablename__ = "lorawan_credentials"

    kg_dev_eui: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("kg_units.dev_eui", ondelete="CASCADE"),
        primary_key=True,
    )
    schema_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    encrypted_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    kg_unit: Mapped["KgUnit"] = relationship(back_populates="lorawan_credentials")

    def __repr__(self) -> str:
        return (
            "LoRaWanCredentials("
            f"kg_dev_eui={self.kg_dev_eui!r}, schema_version={self.schema_version!r})"
        )


# Compatibility exports: prefix/version ownership is app.contexts.production.kg.model.
