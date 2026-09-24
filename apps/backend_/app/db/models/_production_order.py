from __future__ import annotations

from datetime import datetime

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class ProductionOrder(UUIDv7AuditBase):
    """Customer order that production batches are made for."""

    __tablename__ = "production_orders"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )
