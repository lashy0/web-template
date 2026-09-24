from __future__ import annotations

from uuid import UUID

from advanced_alchemy.base import DefaultBase
from advanced_alchemy.mixins import AuditColumns
from sqlalchemy import CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.enums import KgState, enum_values
from app.db.models._batch import Batch
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

    batch: Mapped[Batch] = relationship(lazy="selectin")

    __table_args__ = (CheckConstraint("dev_eui ~ '^[0-9a-f]{16}$'", name="dev_eui_format"),)

    @property
    def activation_type(self) -> ActivationType:
        """The activation type of the batch; read by the API schema."""
        return self.batch.activation_type

    @property
    def lorawan_version(self) -> LoRaWanVersion:
        """The LoRaWAN version of the batch; read by the API schema."""
        return self.batch.lorawan_version
