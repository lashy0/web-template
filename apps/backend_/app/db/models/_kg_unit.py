from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import DefaultBase
from advanced_alchemy.mixins import AuditColumns
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, func, select, text
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db.enums import KgOtkStatus, KgState, enum_values
from app.db.models._batch import Batch
from app.db.models._user import User
from app.lib.lorawan import ActivationType, LoRaWanVersion


class KgUnit(DefaultBase, AuditColumns):
    """One device of a batch, identified by its DevEUI.

    Rows are inserted in bulk when the batch is created and removed with it.
    LoRaWAN keys are not stored: they are derived from the DevEUI on demand.
    The activation type and LoRaWAN version are the same for every unit of a
    batch, so they are read from the batch.
    """

    __tablename__ = "kg_units"

    dev_eui: Mapped[str] = mapped_column(
        String(16),
        primary_key=True,
    )

    short_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
    )

    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    state: Mapped[KgState] = mapped_column(
        Enum(
            KgState,
            name="kg_state",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=KgState.REGISTERED,
    )

    otk_status: Mapped[KgOtkStatus] = mapped_column(
        Enum(
            KgOtkStatus,
            name="kg_otk_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=KgOtkStatus.NOT_VERIFIED,
        server_default=KgOtkStatus.NOT_VERIFIED.value,
        index=True,
    )
    """Set by verification sessions on OTK-line PAKs that pass or fail; the others leave it."""

    last_verification_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    """When the verification that set ``otk_status`` completed."""

    packed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    """Set together with the ``packed`` state and never cleared."""

    packed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    batch: Mapped[Batch] = relationship(lazy="selectin")
    packed_by: Mapped[User | None] = relationship(lazy="selectin")

    __table_args__ = (
        CheckConstraint("dev_eui ~ '^[0-9a-f]{16}$'", name="dev_eui_format"),
        CheckConstraint("(state = 'packed') = (packed_at IS NOT NULL)", name="packed_at_with_packed_state"),
        # Keeps the packed count of a batch proportional to its packed units.
        Index("ix_kg_units_packed_batch_id", "batch_id", postgresql_where=text("state = 'packed'")),
    )

    @property
    def activation_type(self) -> ActivationType:
        """The activation type of the batch; read by the API schema."""
        return self.batch.activation_type

    @property
    def lorawan_version(self) -> LoRaWanVersion:
        """The LoRaWAN version of the batch; read by the API schema."""
        return self.batch.lorawan_version


# Assigned here because ``Batch`` cannot import ``KgUnit``. Only packing
# changes it, never a flush of the batch itself.
Batch.packed_qty = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(KgUnit.batch_id == Batch.id, KgUnit.state == KgState.PACKED)
    .correlate_except(KgUnit)
    .scalar_subquery(),
    expire_on_flush=False,
)
