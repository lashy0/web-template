from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.contexts.production.batches.model import Batch, BatchLoRaWanConfig, BatchStatus
from app.infrastructure.database.base import Base
from app.modules.users.models import User

__all__ = [
    "Batch",
    "BatchLoRaWanConfig",
    "BatchStatus",
    "BatchKeyGenerationJob",
    "BatchKeyGenerationStatus",
    "BatchReceipt",
    "BatchShipment",
    "BatchShipmentItem",
    "ActivationType",
    "LoRaWanVersion",
]


class BatchKeyGenerationStatus(StrEnum):
    CREATING = "CREATING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"


BATCH_KEY_GENERATION_STATUS_DB_TYPE = Enum(
    BatchKeyGenerationStatus,
    name="batch_key_generation_job_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [status.value for status in enum_type],
)


class BatchKeyGenerationJob(Base):
    __tablename__ = "batch_key_generation_jobs"

    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[BatchKeyGenerationStatus] = mapped_column(
        BATCH_KEY_GENERATION_STATUS_DB_TYPE,
        nullable=False,
        default=BatchKeyGenerationStatus.CREATING,
        server_default=BatchKeyGenerationStatus.CREATING.value,
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="batch_key_generation_job_progress_range",
        ),
        Index("ix_batch_key_generation_jobs_status", status),
    )


class BatchReceipt(Base):
    __tablename__ = "batch_receipts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user: Mapped[User | None] = relationship(lazy="selectin")
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="batch_receipt_quantity_positive",
        ),
        Index(
            "ix_batch_receipts_batch_created_at",
            "batch_id",
            "created_at",
        ),
        Index(
            "ix_batch_receipts_voided_at",
            "voided_at",
        ),
    )


class BatchShipment(Base):
    __tablename__ = "batch_shipments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user: Mapped[User | None] = relationship(lazy="selectin")
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "ix_batch_shipments_batch_created_at",
            "batch_id",
            "created_at",
        ),
        Index(
            "ix_batch_shipments_voided_at",
            "voided_at",
        ),
    )


class BatchShipmentItem(Base):
    __tablename__ = "batch_shipment_items"

    shipment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batch_shipments.id"),
        primary_key=True,
    )
    kg_dev_eui: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("kg_units.dev_eui"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_batch_shipment_items_kg_dev_eui",
            "kg_dev_eui",
        ),
    )
