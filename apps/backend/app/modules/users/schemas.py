from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.auth.roles import Role

AuthState = Literal["active", "inactive"]


class UserResponse(BaseModel):
    id: UUID
    identity_id: UUID
    name: str
    role: Role
    login: str | None
    auth_state: AuthState
    auth_state_synced_at: datetime | None
    archived_at: datetime | None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    role: Role
    login: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]{2,63}$")
    password: str = Field(min_length=12)
    active: bool


class UpdateUserRequest(BaseModel):
    login: str | None = Field(
        default=None,
        min_length=3,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9._-]{2,63}$",
    )
    name: str | None = Field(default=None, min_length=1, max_length=128)
    role: Role | None = None


class UpdateActiveRequest(BaseModel):
    active: bool


class UpdateArchivedRequest(BaseModel):
    archived: bool


class UpdatePasswordRequest(BaseModel):
    password: str = Field(min_length=12)
