from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.batch.models import BatchStatus
from app.modules.kg.schemas import DevEui, DevEuiPrefix


class BatchResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    planned_qty: int
    day_plan_qty: int
    status: BatchStatus
    dev_eui_prefix: DevEuiPrefix
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
    planned_qty: int = Field(gt=0)
    day_plan_qty: int = Field(gt=0)

    @field_validator('name', mode='before')
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class UpdateBatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    day_plan_qty: int | None = Field(default=None, gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class UpdateBatchArchivedRequest(BaseModel):
    archived: bool


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
        if isinstance(value, str):
            return value.strip()

        return value


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


class CreateBatchShipmentRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class UpdateBatchShipmentRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class VoidBatchShipmentRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


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
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None


class BatchReceiptListResponse(BaseModel):
    items: list[BatchReceiptResponse]
    total: int


class BatchShipmentListResponse(BaseModel):
    items: list[BatchShipmentResponse]
    total: int
