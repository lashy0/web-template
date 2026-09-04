from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.pak.enums import PakDeviceKind, PakStatus


class PakDeviceResponse(BaseModel):
    id: UUID
    code: str
    kind: PakDeviceKind
    oauth_client_id: str
    status: PakStatus
    last_seen_at: datetime | None
    archived_at: datetime | None


class PakDeviceListResponse(BaseModel):
    items: list[PakDeviceResponse]
    total: int
    page: int
    page_size: int


class CreatePakDeviceRequest(BaseModel):
    code: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    kind: PakDeviceKind
    active: bool = True


class CreatePakDeviceResponse(BaseModel):
    device: PakDeviceResponse
    access_key: str


class PakAccessKeyResponse(BaseModel):
    access_key: str


class UpdatePakDeviceRequest(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    kind: PakDeviceKind | None = None


class UpdateActiveRequest(BaseModel):
    active: bool


class UpdateArchivedRequest(BaseModel):
    archived: bool


class PakTestResponse(BaseModel):
    id: UUID
    test_name: str
    test_label: str
    defect_group_id: UUID
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class PakTestListResponse(BaseModel):
    items: list[PakTestResponse]
    total: int
    page: int
    page_size: int
