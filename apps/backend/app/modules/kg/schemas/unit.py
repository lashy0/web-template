from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ..models import KgStatus
from .common import DevEui


class KgBatchSummaryResponse(BaseModel):
    id: UUID
    name: str


class KgResponse(BaseModel):
    dev_eui: DevEui
    short_id: str
    batch_id: UUID
    batch: KgBatchSummaryResponse
    status: KgStatus
    created_at: datetime
    updated_at: datetime


class KgListResponse(BaseModel):
    items: list[KgResponse]
    total: int
    page: int
    page_size: int


class KgBatchListItemResponse(BaseModel):
    dev_eui: DevEui
    status: KgStatus
    firmware_version: str | None
    last_verification_at: datetime | None


@dataclass(frozen=True, slots=True)
class KgBatchListItem:
    dev_eui: str
    status: KgStatus
    firmware_version: str | None
    last_verification_at: datetime | None


class KgBatchListResponse(BaseModel):
    items: list[KgBatchListItemResponse]
    total: int
    page: int
    page_size: int
