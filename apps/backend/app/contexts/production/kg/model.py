from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class KgDevEuiPrefix(Base):
    __tablename__ = "kg_dev_eui_prefixes"

    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    short_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("prefix ~ '^[0-9a-f]{10}$'", name="kg_dev_eui_prefix_format"),
        Index("ix_kg_dev_eui_prefixes_archived_at", "archived_at"),
        CheckConstraint("short_code ~ '^[a-z0-9]+$'", name="kg_dev_eui_prefix_short_code_format"),
    )


class KgVersion(Base):
    __tablename__ = "kg_versions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_kg_versions_archived_at", "archived_at"),)
