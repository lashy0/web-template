from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class KgStatus(StrEnum):
    REGISTERED = "REGISTERED"

    TESTING = "TESTING"
    TEST_FAILED = "TEST_FAILED"

    IN_ENGINEER_REPAIR = "IN_ENGINEER_REPAIR"
    IN_PRODUCTION_REPAIR = "IN_PRODUCTION_REPAIR"

    READY_FOR_RETEST = "READY_FOR_RETEST"

    READY_FOR_PACKING = "READY_FOR_PACKING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"

    SCRAPPED = "SCRAPPED"


KG_STATUS_DB_TYPE = Enum(
    KgStatus,
    name="kg_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [status.value for status in enum_type],
)


class KgUnit(Base):
    __tablename__ = "kg_units"

    dev_eui: Mapped[str] = mapped_column(String(16), primary_key=True)
    short_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id"),
        nullable=False,
    )
    status: Mapped[KgStatus] = mapped_column(
        KG_STATUS_DB_TYPE,
        nullable=False,
        default=KgStatus.REGISTERED,
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
            "dev_eui ~ '^[0-9a-f]{16}$'",
            name="dev_eui_format",
        ),
        Index("ix_kg_units_batch_id", "batch_id"),
        Index("ix_kg_units_status", "status"),
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

    __table_args__ = (
        CheckConstraint(
            "prefix ~ '^[0-9a-f]{10}$'",
            name="kg_dev_eui_prefix_format",
        ),
        CheckConstraint(
            "short_code ~ '^[a-z0-9]+$'",
            name="kg_dev_eui_prefix_short_code_format",
        ),
    )
