from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

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


class KgDevEuiPrefix(Base):
    __tablename__ = "kg_dev_eui_prefixes"

    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    short_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "prefix ~ '^[0-9a-f]{10}$'",
            name="kg_dev_eui_prefix_format",
        ),
        Index("ix_kg_dev_eui_prefixes_archived_at", "archived_at"),
        CheckConstraint(
            "short_code ~ '^[a-z0-9]+$'",
            name="kg_dev_eui_prefix_short_code_format",
        ),
    )


class KgVersion(Base):
    __tablename__ = "kg_versions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (Index("ix_kg_versions_archived_at", "archived_at"),)
