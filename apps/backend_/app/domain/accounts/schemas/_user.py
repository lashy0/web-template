"""User-related account schemas."""

from datetime import datetime
from uuid import UUID

import msgspec

from app.db.enums import UserRole
from app.lib.schema import CamelizedBaseStruct
from app.lib.validation import (
    validate_login,
    validate_name,
    validate_password,
)


class User(CamelizedBaseStruct):
    """User properties to use for a response."""

    id: UUID
    identity_id: UUID
    login: str
    name: str
    role: UserRole
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserCreate(CamelizedBaseStruct):
    """Data required to create a user."""

    login: str
    name: str
    role: UserRole
    password: str
    is_active: bool = True

    def __post_init__(self) -> None:
        self.login = validate_login(self.login)
        self.password = validate_password(self.password)
        self.name = validate_name(self.name)


class UserUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Administrative update of an existing user."""

    login: str | msgspec.UnsetType = msgspec.UNSET
    name: str | msgspec.UnsetType = msgspec.UNSET
    role: UserRole | msgspec.UnsetType = msgspec.UNSET

    def __post_init__(self) -> None:
        fields = (
            self.login,
            self.name,
            self.role,
        )

        if all(field is msgspec.UNSET for field in fields):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.login, str):
            self.login = validate_login(self.login)

        if isinstance(self.name, str):
            self.name = validate_name(self.name)


class ProfileUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Update the current user's profile."""

    name: str | msgspec.UnsetType = msgspec.UNSET

    def __post_init__(self) -> None:
        if isinstance(self.name, str):
            self.name = validate_name(self.name)


class UserPasswordUpdate(CamelizedBaseStruct):
    """Update a user's Kratos password."""

    password: str

    def __post_init__(self) -> None:
        self.password = validate_password(self.password)


class UserActiveUpdate(CamelizedBaseStruct):
    """Enable or disable a user's Kratos identity."""

    is_active: bool


class UserArchivedUpdate(CamelizedBaseStruct):
    """Archive or restore an application user."""

    archived: bool
