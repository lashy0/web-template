from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductionOrderSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    archived_at: datetime | None


class ProductionOrderResponse(ProductionOrderSummaryResponse):
    description: str | None
    created_at: datetime
    updated_at: datetime
    batches_count: int
    total_planned_qty: int


class ProductionOrderListResponse(BaseModel):
    items: list[ProductionOrderResponse]
    total: int
    page: int
    page_size: int


class CreateProductionOrderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class UpdateProductionOrderRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if value is None:
            raise ValueError("name cannot be null")
        return value.strip() if isinstance(value, str) else value


class UpdateProductionOrderArchivedRequest(BaseModel):
    archived: bool


class AssignProductionOrderRequest(BaseModel):
    production_order_id: UUID | None
