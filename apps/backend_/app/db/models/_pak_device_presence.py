from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import DefaultBase
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class PakDevicePresence(DefaultBase):
    """When a PAK device last reached the API.

    Kept apart from ``PakDevice`` so that recording every machine request
    neither touches the device's ``updated_at`` nor waits on edits of it.
    """

    __tablename__ = "pak_device_presence"

    pak_id: Mapped[UUID] = mapped_column(
        ForeignKey("pak_devices.id", ondelete="CASCADE"),
        primary_key=True,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )
