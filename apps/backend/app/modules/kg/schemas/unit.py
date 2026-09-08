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
