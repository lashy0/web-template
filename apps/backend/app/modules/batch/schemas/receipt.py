from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .common import normalize_trimmed


class CreateBatchReceiptRequest(BaseModel):
    quantity: int = Field(gt=0)
    comment: str | None = Field(default=None, max_length=2000)


class UpdateBatchReceiptRequest(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    comment: str | None = Field(default=None, max_length=2000)


class VoidBatchReceiptRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return normalize_trimmed(value)


class BatchReceiptResponse(BaseModel):
    id: UUID
    batch_id: UUID
    quantity: int
    comment: str | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    voided_at: datetime | None
    void_reason: str | None


class BatchReceiptListResponse(BaseModel):
    items: list[BatchReceiptResponse]
    total: int
