"""Stable batch HTTP schemas owned by the production context."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.domains.identity.users.schemas import UserSummaryResponse
from app.domains.production.kg.schemas import (
    DevEuiPrefix,
    KgDevEuiPrefixSummaryResponse,
    KgVersionSummaryResponse,
)
from app.domains.production.orders.schemas import ProductionOrderSummaryResponse
from app.domains.production.preparation.model import BatchKeyGenerationStatus

from .model import BatchStatus


def _normalize_trimmed(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class BatchLoRaWanConfigResponse(BaseModel):
    activation_type: ActivationType
    lorawan_version: LoRaWanVersion
    join_eui: str


class CreateBatchLoRaWanConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activation_type: ActivationType
    lorawan_version: LoRaWanVersion


class BatchResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    planned_qty: int
    day_plan_qty: int
    status: BatchStatus
    preparation_status: BatchKeyGenerationStatus
    preparation_progress: int
    preparation_error_code: str | None
    lorawan_config: BatchLoRaWanConfigResponse | None
    dev_eui_prefix: KgDevEuiPrefixSummaryResponse
    kg_version: KgVersionSummaryResponse | None
    production_order_id: UUID | None = None
    production_order: ProductionOrderSummaryResponse | None = None
    created_by_user_id: UUID | None
    created_by_user: UserSummaryResponse | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    archived_at: datetime | None
    can_delete: bool


class BatchListResponse(BaseModel):
    items: list[BatchResponse]
    total: int
    page: int
    page_size: int


class DevEuiRangePreviewResponse(BaseModel):
    first_dev_eui: str
    last_dev_eui: str


class CreateBatchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    dev_eui_prefix: DevEuiPrefix
    kg_version_id: UUID | None = None
    production_order_id: UUID | None = None
    planned_qty: int = Field(gt=0)
    day_plan_qty: int = Field(gt=0)
    lorawan_config: CreateBatchLoRaWanConfigRequest

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return _normalize_trimmed(value)


class UpdateBatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    day_plan_qty: int | None = Field(default=None, gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return _normalize_trimmed(value)


class UpdateBatchArchivedRequest(BaseModel):
    archived: bool
