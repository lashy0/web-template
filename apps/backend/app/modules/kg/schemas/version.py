from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateKgVersionRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("code", "name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class UpdateKgVersionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class KgVersionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    batch_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class KgVersionSummaryResponse(BaseModel):
    id: UUID
    code: str
    name: str


class KgVersionListResponse(BaseModel):
    items: list[KgVersionResponse]
    total: int
    page: int
    page_size: int


class UpdateKgVersionArchivedRequest(BaseModel):
    archived: bool
