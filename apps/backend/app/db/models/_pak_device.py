from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import Boolean, Enum, Index, String, select
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.db.enums import PakDeviceKind, enum_values
from app.db.models._pak_device_presence import PakDevicePresence


class PakDevice(UUIDv7AuditBase):
    """Programmable inspection and control device registered in the system."""

    __tablename__ = "pak_devices"

    code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )

    kind: Mapped[PakDeviceKind] = mapped_column(
        Enum(
            PakDeviceKind,
            name="pak_device_kind",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )

    oauth_client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    encrypted_access_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    if TYPE_CHECKING:
        last_seen_at: datetime | None
        """When the device last reached the API; mapped below the class."""

    __table_args__ = (
        Index("ix_pak_devices_kind", "kind"),
        Index("ix_pak_devices_is_active", "is_active"),
    )


# Assigned after the class so the subquery can reference ``PakDevice.id``.
# ``PakDeviceService.record_seen`` writes the presence row, never a flush of
# the device itself.
PakDevice.last_seen_at = column_property(  # type: ignore[assignment]
    select(PakDevicePresence.last_seen_at)
    .where(PakDevicePresence.pak_id == PakDevice.id)
    .correlate_except(PakDevicePresence)
    .scalar_subquery(),
    expire_on_flush=False,
)
