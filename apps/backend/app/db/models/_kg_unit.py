from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import DefaultBase
from advanced_alchemy.mixins import AuditColumns
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, and_, func, select, text
from sqlalchemy.orm import Mapped, column_property, foreign, mapped_column, relationship

from app.db.enums import KgOtkStatus, KgState, PakDeviceKind, VerificationSessionStatus, enum_values
from app.db.models._batch import Batch
from app.db.models._kg_version import KgVersion
from app.db.models._user import User
from app.db.models._verification_session import VerificationSession
from app.lib.audit import AuditTarget
from app.lib.lorawan import ActivationType, LoRaWanVersion

if TYPE_CHECKING:
    from app.db.models._batch_shipment import BatchShipment


class KgUnit(DefaultBase, AuditColumns, AuditTarget):
    """One device of a batch, identified by its DevEUI.

    Rows are inserted in bulk when the batch is created and removed with it.
    LoRaWAN keys are not stored: they are derived from the DevEUI on demand.
    The activation type, LoRaWAN version and KG version are the same for
    every unit of a batch, so they are read from the batch.
    """

    __tablename__ = "kg_units"

    __audit_type__ = "kg_unit"
    __audit_id__ = "dev_eui"
    __audit_label__ = "short_id"

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
    """Set together with the ``packed`` state and kept once the unit is shipped."""

    packed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    batch: Mapped[Batch] = relationship(lazy="selectin")
    packed_by: Mapped[User | None] = relationship(lazy="selectin")
    running_otk: Mapped[VerificationSession | None] = relationship(
        primaryjoin=lambda: and_(
            KgUnit.dev_eui == foreign(VerificationSession.dev_eui),
            VerificationSession.status == VerificationSessionStatus.RUNNING,
            VerificationSession.pak_kind == PakDeviceKind.OTK_LINE,
        ),
        viewonly=True,
        lazy="selectin",
    )
    """The verification running on an OTK-line PAK now; a unit runs at most one session."""

    if TYPE_CHECKING:
        shipment: Mapped[BatchShipment | None]
        """The completed shipment that shipped the unit; mapped in the shipments module."""

    __table_args__ = (
        CheckConstraint("dev_eui ~ '^[0-9a-f]{16}$'", name="dev_eui_format"),
        CheckConstraint(
            "(state IN ('packed', 'shipped')) = (packed_at IS NOT NULL)",
            name="packed_at_with_packed_state",
        ),
        # Keep the packed and shipped counts of a batch proportional to those units.
        Index("ix_kg_units_packed_batch_id", "batch_id", postgresql_where=text("state IN ('packed', 'shipped')")),
        Index("ix_kg_units_shipped_batch_id", "batch_id", postgresql_where=text("state = 'shipped'")),
    )

    @property
    def activation_type(self) -> ActivationType:
        """The activation type of the batch; read by the API schema."""
        return self.batch.activation_type

    @property
    def lorawan_version(self) -> LoRaWanVersion:
        """The LoRaWAN version of the batch; read by the API schema."""
        return self.batch.lorawan_version

    @property
    def kg_version(self) -> KgVersion | None:
        """The KG version of the batch; read by the API schema."""
        return self.batch.kg_version


# Assigned here because ``Batch`` cannot import ``KgUnit``. Only packing and
# shipments change them, never a flush of the batch itself. A shipped unit
# stays counted as packed.
Batch.packed_qty = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(
        KgUnit.batch_id == Batch.id,
        KgUnit.state.in_((KgState.PACKED, KgState.SHIPPED)),
    )
    .correlate_except(KgUnit)
    .scalar_subquery(),
    expire_on_flush=False,
)
Batch.shipped_qty = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(
        KgUnit.batch_id == Batch.id,
        KgUnit.state == KgState.SHIPPED,
    )
    .correlate_except(KgUnit)
    .scalar_subquery(),
    expire_on_flush=False,
)
# Verification changes them. Packing needs a passed OTK and ends OTK-line
# verification, so packed and shipped units count as passed.
Batch.otk_passed_qty = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(
        KgUnit.batch_id == Batch.id,
        KgUnit.otk_status == KgOtkStatus.PASSED,
        KgUnit.state != KgState.SCRAPPED,
    )
    .correlate_except(KgUnit)
    .scalar_subquery(),
    expire_on_flush=False,
)
Batch.otk_failed_qty = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(
        KgUnit.batch_id == Batch.id,
        KgUnit.otk_status == KgOtkStatus.FAILED,
        KgUnit.state == KgState.REGISTERED,
    )
    .correlate_except(KgUnit)
    .scalar_subquery(),
    expire_on_flush=False,
)
