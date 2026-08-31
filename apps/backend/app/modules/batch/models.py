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
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class BatchStatus(StrEnum):
    IN_PRODUCTION = "IN_PRODUCTION"
    COMPLETED = "COMPLETED"


BATCH_STATUS_DB_TYPE = Enum(
    BatchStatus,
    name="batch_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [status.value for status in enum_type]
)


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    day_plan_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BatchStatus] = mapped_column(
        BATCH_STATUS_DB_TYPE,
        nullable=False,
        default=BatchStatus.IN_PRODUCTION,
    )
    dev_eui_prefix: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("kg_dev_eui_prefixes.prefix"),
        nullable=False,
    )
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
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "planned_qty  > 0",
            name="batch_planned_qty_positive",
        ),
        CheckConstraint(
            "day_plan_qty  > 0",
            name="batch_day_plan_qty_positive",
        ),
        Index("ix_batches_status", status),
        Index("ix_batches_created_at", created_at),
        Index("ix_batches_archived_at", archived_at),
        Index("ix_batches_dev_eui_prefix", dev_eui_prefix),
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
        )
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
