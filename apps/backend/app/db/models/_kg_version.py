from __future__ import annotations

from datetime import datetime

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.lib.audit import AuditTarget


class KgVersion(UUIDv7AuditBase, AuditTarget):
    """Hardware version of the KG units a batch produces."""

    __tablename__ = "kg_versions"

    __audit_type__ = "kg_version"
    __audit_label__ = "code"
    __audit_name__ = "name"

    code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
    )

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
