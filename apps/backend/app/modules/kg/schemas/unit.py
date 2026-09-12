from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ..models import KgState
from .common import DevEui
from .state import KgCurrentState


class KgBatchSummaryResponse(BaseModel):
    id: UUID
    name: str


class KgResponse(BaseModel):
    dev_eui: DevEui
    short_id: str
    batch_id: UUID
    batch: KgBatchSummaryResponse
    state: KgState
    current_state: KgCurrentState
    created_at: datetime
    updated_at: datetime


class KgListResponse(BaseModel):
    items: list[KgResponse]
    total: int
    page: int
    page_size: int


class KgBatchListItemResponse(BaseModel):
    dev_eui: DevEui
    current_state: KgCurrentState
    firmware_version: str | None
    last_verification_at: datetime | None


@dataclass(frozen=True, slots=True)
class KgBatchListItem:
    dev_eui: str
    current_state: KgCurrentState
    firmware_version: str | None
    last_verification_at: datetime | None


class KgBatchListResponse(BaseModel):
    items: list[KgBatchListItemResponse]
    total: int
    page: int
    page_size: int
