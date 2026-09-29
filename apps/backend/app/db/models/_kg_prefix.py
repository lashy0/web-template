from __future__ import annotations

from datetime import datetime

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.lib.lorawan import DEV_EUI_SERIAL_MAX


class KgPrefix(UUIDv7AuditBase):
    """DevEUI prefix that KG units of a batch are allocated from.

    ``prefix`` and ``short_code`` never change: DevEUIs start with the prefix and
    every KG short ID is built from the short code. ``next_serial`` only grows:
    a DevEUI once allocated is never issued again, even after its batch is
    deleted.
    """

    __tablename__ = "kg_prefixes"

    prefix: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
    )

    short_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    next_serial: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    __table_args__ = (
        CheckConstraint("prefix ~ '^[0-9a-f]{10}$'", name="prefix_format"),
        CheckConstraint("short_code ~ '^[a-z0-9]+$'", name="short_code_format"),
        CheckConstraint(f"next_serial BETWEEN 1 AND {DEV_EUI_SERIAL_MAX + 1}", name="next_serial_range"),
    )

    @property
    def available_qty(self) -> int:
        """How many DevEUIs are left to allocate; read by the API schema."""
        return DEV_EUI_SERIAL_MAX - self.next_serial + 1
