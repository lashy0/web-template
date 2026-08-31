from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Index,
    String,
    Uuid,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    __table_args__ = (
        Index(
            "ix_audit_events_entity",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_audit_events_entity_type_created_at",
            "entity_type",
            desc("created_at"),
        ),
        Index(
            "ix_audit_events_actor",
            "actor_type",
            "actor_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
