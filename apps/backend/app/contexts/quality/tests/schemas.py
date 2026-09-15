from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.contexts.quality.defects.schemas import DefectGroupSummaryResponse


class PakTestResponse(BaseModel):
    id: UUID
    test_name: str
    test_label: str
    defect_group_id: UUID
    defect_group: DefectGroupSummaryResponse
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class PakTestListResponse(BaseModel):
    items: list[PakTestResponse]
    total: int
    page: int
    page_size: int
