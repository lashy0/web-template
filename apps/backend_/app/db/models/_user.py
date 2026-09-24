from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.enums import UserRole, enum_values


class User(UUIDv7AuditBase):
    """Application user associated with a Kratos identity."""

    __tablename__ = "user_account"

    __table_args__ = ({"comment": "Application users associated with Kratos identities"},)

    identity_id: Mapped[UUID] = mapped_column(
        unique=True,
        nullable=False,
    )

    identity_login: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    identity_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        default=None,
    )
