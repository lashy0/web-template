from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._user import User


class BatchReceipt(UUIDv7AuditBase):
    """A quantity of KG units of one batch accepted from production.

    A voided receipt stays for the record and no longer counts as received.
    """

    __tablename__ = "batch_receipts"

    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    voided_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    void_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[User | None] = relationship(lazy="selectin")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("(voided_at IS NULL) = (void_reason IS NULL)", name="void_reason_with_voided_at"),
        Index("ix_batch_receipts_batch_id_created_at", "batch_id", "created_at"),
    )
