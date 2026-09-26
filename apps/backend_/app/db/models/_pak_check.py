from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.db.models._defect_group import DefectGroup


class PakCheck(UUIDv7AuditBase):
    """A check that PAKs run, as they last reported it.

    PAKs define checks, not users: a row is created the first time a PAK
    starts a verification step with the check's ``name`` and ``label`` and
    follows what PAKs report afterwards. A PAK reuses one name for variants of
    a check, such as ``TestDimming`` at 0% to 100%, so the label is part of
    the identity.
    """

    __tablename__ = "pak_checks"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    defect_group_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    """The defect group code last reported for the check, matched or not."""

    defect_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("defect_groups.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    """The active group with ``defect_group_code``; empty when no such group exists."""

    last_seen_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    defect_group: Mapped[DefectGroup | None] = relationship(lazy="selectin")

    __table_args__ = (UniqueConstraint("name", "label", name="uq_pak_checks_name_label"),)

    @property
    def misconfigured(self) -> bool:
        """Whether the reported defect group code matched no active group; read by the API schema."""
        return self.defect_group_id is None
