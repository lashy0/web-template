from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.enums import BatchStatus, enum_values
from app.db.models._kg_prefix import KgPrefix
from app.db.models._kg_version import KgVersion
from app.db.models._production_order import ProductionOrder
from app.db.models._user import User
from app.lib.lorawan import DEV_EUI_SERIAL_MAX, ActivationType, LoRaWanVersion, derive_dev_eui_range


class Batch(UUIDv7AuditBase):
    """A production run of KG units with one contiguous DevEUI range.

    The range starts at ``first_serial`` under ``kg_prefix`` and holds
    ``planned_qty`` serials; it is allocated at creation and never changes.
    """

    __tablename__ = "batches"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    planned_qty: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    day_plan_qty: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[BatchStatus] = mapped_column(
        Enum(
            BatchStatus,
            name="batch_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=BatchStatus.IN_PRODUCTION,
    )

    kg_prefix_id: Mapped[UUID] = mapped_column(
        ForeignKey("kg_prefixes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    first_serial: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    kg_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("kg_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    production_order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("production_orders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    activation_type: Mapped[ActivationType] = mapped_column(
        Enum(
            ActivationType,
            name="activation_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )

    lorawan_version: Mapped[LoRaWanVersion] = mapped_column(
        Enum(
            LoRaWanVersion,
            name="lorawan_version",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )

    join_eui: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        unique=True,
    )

    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    kg_prefix: Mapped[KgPrefix] = relationship(lazy="selectin")
    kg_version: Mapped[KgVersion | None] = relationship(lazy="selectin")
    production_order: Mapped[ProductionOrder | None] = relationship(lazy="selectin")
    created_by: Mapped[User | None] = relationship(lazy="selectin")

    __table_args__ = (
        CheckConstraint("planned_qty > 0", name="planned_qty_positive"),
        CheckConstraint("day_plan_qty > 0", name="day_plan_qty_positive"),
        CheckConstraint(
            f"first_serial >= 1 AND first_serial + planned_qty - 1 <= {DEV_EUI_SERIAL_MAX}",
            name="serial_range",
        ),
        CheckConstraint("join_eui ~ '^[0-9a-f]{16}$'", name="join_eui_format"),
    )

    @property
    def first_dev_eui(self) -> str:
        """The first DevEUI of the batch range; read by the API schema."""
        return derive_dev_eui_range(self.kg_prefix.prefix, self.planned_qty, first_serial=self.first_serial)[0]

    @property
    def last_dev_eui(self) -> str:
        """The last DevEUI of the batch range; read by the API schema."""
        return derive_dev_eui_range(self.kg_prefix.prefix, self.planned_qty, first_serial=self.first_serial)[1]
