from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domains.quality.defects.model import DefectGroup
from app.infrastructure.database.base import Base


class Check(Base):
    __tablename__ = "pak_tests"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    defect_group: Mapped[DefectGroup] = relationship(lazy="selectin")
    test_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    test_label: Mapped[str] = mapped_column(String(255), nullable=False)
    defect_group_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("defect_groups.id", ondelete="RESTRICT"), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_pak_tests_defect_group_id", "defect_group_id"),)
