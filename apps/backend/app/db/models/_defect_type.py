from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.db.models._defect_group import DefectGroup


class DefectType(UUIDv7AuditBase):
    """A specific defect with guidance for the engineer who repairs it."""

    __tablename__ = "defect_types"

    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("defect_groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    possible_cause: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    engineer_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    group: Mapped[DefectGroup] = relationship(lazy="selectin")
