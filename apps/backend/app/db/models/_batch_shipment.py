from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import DefaultBase, UUIDv7AuditBase
from advanced_alchemy.mixins import AuditColumns
from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    and_,
    func,
    select,
    text,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db.enums import BatchShipmentStatus, enum_values
from app.db.models._kg_unit import KgUnit
from app.db.models._user import User
from app.lib.audit import AuditTarget


class BatchShipment(UUIDv7AuditBase, AuditTarget):
    """A document that ships packed KG units of one batch.

    An open shipment collects units; completing it ships them. A voided
    shipment stays for the record and releases its units.
    """

    __tablename__ = "batch_shipments"

    __audit_type__ = "batch_shipment"
    __audit_label__ = "number"

    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )

    number: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True),
        nullable=False,
        unique=True,
    )
    """Sequential number across all batches for paperwork, assigned by the database."""

    status: Mapped[BatchShipmentStatus] = mapped_column(
        Enum(
            BatchShipmentStatus,
            name="batch_shipment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=BatchShipmentStatus.OPEN,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    completed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    voided_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    voided_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    void_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[User | None] = relationship(lazy="selectin", foreign_keys=[created_by_id])
    completed_by: Mapped[User | None] = relationship(lazy="selectin", foreign_keys=[completed_by_id])
    voided_by: Mapped[User | None] = relationship(lazy="selectin", foreign_keys=[voided_by_id])

    if TYPE_CHECKING:
        quantity: int
        """KG units in the shipment; mapped below the item class."""

    __table_args__ = (
        CheckConstraint(
            "(status = 'open' AND completed_at IS NULL) OR (status = 'completed' AND completed_at IS NOT NULL) "
            "OR status = 'voided'",
            name="completed_at_with_status",
        ),
        CheckConstraint("(status = 'voided') = (voided_at IS NOT NULL)", name="voided_at_with_status"),
        CheckConstraint("(voided_at IS NULL) = (void_reason IS NULL)", name="void_reason_with_voided_at"),
        Index("ix_batch_shipments_batch_id_created_at", "batch_id", "created_at"),
    )


class BatchShipmentItem(DefaultBase, AuditColumns):
    """A KG unit put into a shipment of its batch.

    ``voided_at`` is set when the shipment is voided; the item then stays for
    the record and the unit may go into another shipment. A partial unique
    index keeps a unit in at most one shipment that is not voided.
    """

    __tablename__ = "batch_shipment_items"

    shipment_id: Mapped[UUID] = mapped_column(
        ForeignKey("batch_shipments.id", ondelete="CASCADE"),
        primary_key=True,
    )

    dev_eui: Mapped[str] = mapped_column(
        ForeignKey("kg_units.dev_eui", ondelete="RESTRICT"),
        primary_key=True,
    )

    voided_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    added_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    """Who put the unit into the shipment."""

    kg_unit: Mapped[KgUnit] = relationship(lazy="selectin")
    added_by: Mapped[User | None] = relationship(lazy="selectin")

    __table_args__ = (
        Index(
            "uq_batch_shipment_items_dev_eui_not_voided",
            "dev_eui",
            unique=True,
            postgresql_where=text("voided_at IS NULL"),
        ),
        Index("ix_batch_shipment_items_shipment_id_created_at", "shipment_id", "created_at"),
    )

    @property
    def short_id(self) -> str:
        """The short ID of the unit; read by the API schema."""
        return self.kg_unit.short_id


# Assigned after the item class so the subquery can reference it. Only the
# items change it, never a flush of the shipment itself.
BatchShipment.quantity = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(BatchShipmentItem.shipment_id == BatchShipment.id)
    .correlate_except(BatchShipmentItem)
    .scalar_subquery(),
    expire_on_flush=False,
)

# Assigned here because ``KgUnit`` cannot import the shipments. A shipped unit
# is in exactly one completed shipment whose item is not voided.
KgUnit.shipment = relationship(
    BatchShipment,
    secondary=BatchShipmentItem.__table__,
    primaryjoin=lambda: and_(
        KgUnit.dev_eui == BatchShipmentItem.dev_eui,
        BatchShipmentItem.voided_at.is_(None),
    ),
    secondaryjoin=lambda: and_(
        BatchShipmentItem.shipment_id == BatchShipment.id,
        BatchShipment.status == BatchShipmentStatus.COMPLETED,
    ),
    uselist=False,
    viewonly=True,
    lazy="selectin",
)
