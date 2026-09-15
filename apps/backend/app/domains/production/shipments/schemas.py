"""Stable shipment request/response schemas, re-exported by the legacy API package."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domains.identity.users.schemas import UserSummaryResponse
from app.domains.production.kg.schemas import DevEui


def normalize_trimmed(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class CreateBatchShipmentRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class UpdateBatchShipmentRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class VoidBatchShipmentRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return normalize_trimmed(value)


class AddBatchShipmentItemRequest(BaseModel):
    dev_eui: DevEui


class BatchShipmentItemResponse(BaseModel):
    shipment_id: UUID
    kg_dev_eui: DevEui
    created_at: datetime


class BatchShipmentResponse(BaseModel):
    id: UUID
    batch_id: UUID
    comment: str | None
    quantity: int
    created_by_user_id: UUID | None
    created_by_user: UserSummaryResponse | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None


class BatchShipmentListResponse(BaseModel):
    items: list[BatchShipmentResponse]
    total: int
