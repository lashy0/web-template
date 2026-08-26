from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.roles import Role
from app.infrastructure.database.base import Base

ROLE_DB_TYPE = Enum(
    Role,
    name="user_role",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum_type: [role.value for role in enum_type],
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    identity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    role: Mapped[Role] = mapped_column(ROLE_DB_TYPE, nullable=False)
    identity_login: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auth_state: Mapped[str] = mapped_column(String(16), nullable=False, default="inactive")
    auth_state_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "auth_state IN ('active', 'inactive')",
            name="auth_state_allowed_values",
        ),
        Index("ix_users_auth_state", "auth_state"),
        Index("ix_users_identity_login", "identity_login"),
    )
