from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class PakDeviceKind(StrEnum):
    ENGINEERING = "ENGINEERING"
    OTK_LINE = "OTK_LINE"


PAK_DEVICE_KIND_DB_TYPE = Enum(
    PakDeviceKind,
    name="pak_device_kind",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [kind.value for kind in enum_type],
)


class PakDevice(Base):
    __tablename__ = "pak_devices"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    kind: Mapped[PakDeviceKind] = mapped_column(PAK_DEVICE_KIND_DB_TYPE, nullable=False)
    oauth_client_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    encrypted_access_key: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_pak_devices_code", "code"),
        Index("ix_pak_devices_oauth_client_id", "oauth_client_id"),
        Index("ix_pak_devices_kind", "kind"),
        Index("ix_pak_devices_is_active", "is_active"),
    )
