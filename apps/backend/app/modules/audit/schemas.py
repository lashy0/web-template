from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: UUID
    created_at: datetime

    actor_type: str
    actor_id: str | None
    actor_display_name: str | None
    actor_identifier: str | None

    action: str

    entity_type: str
    entity_id: str | None
    entity_display_name: str | None
    entity_identifier: str | None

    old_data: dict[str, Any] | None
    new_data: dict[str, Any] | None


class AuditListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int
