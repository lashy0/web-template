from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import String, Text, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.db.models._defect_type import DefectType


class DefectGroup(UUIDv7AuditBase):
    """A class of defects; a PAK reports a failed check by the group's code."""

    __tablename__ = "defect_groups"

    code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
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

    if TYPE_CHECKING:
        types_count: int
        """Defect types of the group; mapped below the class."""

        active_types_count: int
        """Defect types of the group that are not archived; mapped below the class."""


# Assigned after the class so the subqueries can reference ``DefectGroup.id``.
DefectGroup.types_count = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(
        DefectType.group_id == DefectGroup.id
    )
    .correlate_except(DefectType)
    .scalar_subquery(),
    expire_on_flush=False,
)
DefectGroup.active_types_count = column_property(  # type: ignore[assignment]
    select(func.count())
    .where(
        DefectType.group_id == DefectGroup.id,
        DefectType.archived_at.is_(None),
    )
    .correlate_except(DefectType)
    .scalar_subquery(),
    expire_on_flush=False,
)
