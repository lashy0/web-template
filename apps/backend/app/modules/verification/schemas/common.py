from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.kg.schemas import DevEui
from app.modules.verification.models import (
    VerificationSessionStatus,
    VerificationStepStatus,
)


class VerificationStepResponse(BaseModel):
    id: UUID
    session_id: UUID
    step_no: int
    pak_test_id: UUID
    defect_group_id: UUID
    test_name: str
    test_label: str
    error_group_code: str
    status: VerificationStepStatus
    measurement_value: float | None
    measurement_min_value: float | None
    measurement_max_value: float | None
    measurement_unit: str | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VerificationSessionResponse(BaseModel):
    id: UUID
    kg_dev_eui: DevEui
    pak_id: UUID
    slot_no: int
    firmware_version: str
    total_steps: int
    status: VerificationSessionStatus
    started_at: datetime
    last_activity_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VerificationSessionDetailResponse(VerificationSessionResponse):
    steps: list[VerificationStepResponse]


class VerificationSessionListResponse(BaseModel):
    items: list[VerificationSessionResponse]
    total: int
    page: int
    page_size: int
