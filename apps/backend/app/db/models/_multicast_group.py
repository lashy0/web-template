from __future__ import annotations

from datetime import datetime

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import CheckConstraint, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.lib.audit import AuditTarget
from app.lib.lorawan import (
    MULTICAST_GROUP_IDS,
    MulticastSessionKeys,
    derive_multicast_session_keys,
)


class MulticastGroup(UUIDv7AuditBase, AuditTarget):
    """LoRaWAN multicast group that KG units of batches are provisioned with.

    Every batch uses one group of each ``group_id``; several batches may share a
    group. ``mc_addr`` and ``mc_key`` are generated and never change; the
    session keys are derived from them.
    """

    __tablename__ = "multicast_groups"

    __audit_type__ = "multicast_group"
    __audit_label__ = "name"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )

    group_id: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    mc_addr: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        unique=True,
    )

    mc_key: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    frequency_hz: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    datarate: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(f"group_id IN ({', '.join(map(str, MULTICAST_GROUP_IDS))})", name="group_id_range"),
        CheckConstraint("mc_addr ~ '^[0-9a-f]{8}$'", name="mc_addr_format"),
        CheckConstraint("mc_key ~ '^[0-9a-f]{32}$'", name="mc_key_format"),
        CheckConstraint("frequency_hz > 0", name="frequency_hz_positive"),
        CheckConstraint("datarate BETWEEN 0 AND 15", name="datarate_range"),
    )

    @property
    def session_keys(self) -> MulticastSessionKeys:
        """The McNwkSKey and McAppSKey of the group."""
        return derive_multicast_session_keys(self.mc_addr, self.mc_key)
