from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domains.identity.users.model import User
from app.infrastructure.database.base import Base


class BatchShipment(Base):
    """Persisted shipment document; table ownership belongs to production.shipments."""

    __tablename__ = "batch_shipments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("batches.id"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user: Mapped[User | None] = relationship(lazy="selectin")
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_batch_shipments_batch_created_at", "batch_id", "created_at"),
        Index("ix_batch_shipments_voided_at", "voided_at"),
    )


class BatchShipmentItem(Base):
    __tablename__ = "batch_shipment_items"

    shipment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("batch_shipments.id"), primary_key=True
    )
    kg_dev_eui: Mapped[str] = mapped_column(
        String(16), ForeignKey("kg_units.dev_eui"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_batch_shipment_items_kg_dev_eui", "kg_dev_eui"),)
