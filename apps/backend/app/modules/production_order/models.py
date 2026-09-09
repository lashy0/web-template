from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ProductionOrder(Base):
    __tablename__ = "production_orders"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_production_orders_archived_at", archived_at),
        Index("ix_production_orders_created_at", created_at),
    )
