from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.kg.schemas import DevEuiPrefix

from ..models import BatchStatus
from .common import normalize_trimmed


class BatchResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    planned_qty: int
    day_plan_qty: int
    status: BatchStatus
    dev_eui_prefix: DevEuiPrefix
    kg_version_id: UUID | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    archived_at: datetime | None


class BatchListResponse(BaseModel):
    items: list[BatchResponse]
    total: int
    page: int
    page_size: int


class CreateBatchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    dev_eui_prefix: DevEuiPrefix
    kg_version_id: UUID | None = None
    planned_qty: int = Field(gt=0)
    day_plan_qty: int = Field(gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return normalize_trimmed(value)


class UpdateBatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    day_plan_qty: int | None = Field(default=None, gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return normalize_trimmed(value)


class UpdateBatchArchivedRequest(BaseModel):
    archived: bool
