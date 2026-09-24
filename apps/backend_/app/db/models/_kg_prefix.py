from __future__ import annotations

from datetime import datetime

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column


class KgPrefix(UUIDv7AuditBase):
    """DevEUI prefix that KG units of a batch are allocated from.

    ``prefix`` and ``short_code`` never change: DevEUIs start with the prefix and
    every KG short ID is built from the short code.
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

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    __table_args__ = (
        CheckConstraint("prefix ~ '^[0-9a-f]{10}$'", name="prefix_format"),
        CheckConstraint("short_code ~ '^[a-z0-9]+$'", name="short_code_format"),
    )
