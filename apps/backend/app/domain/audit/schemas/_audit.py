"""Audit log schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.lib.schema import CamelizedBaseStruct


class AuditLogEntry(CamelizedBaseStruct, kw_only=True):
    """Detailed audit log entry."""

    id: UUID
    action: str
    created_at: datetime

    actor_id: UUID | None
    actor_login: str | None
    actor_name: str | None

    target_type: str | None
    target_id: str | None
    target_label: str | None
    target_name: str | None
    target_current_label: str | None = None
    """The target's label today, when it has changed since the entry was written."""

    details: dict[str, Any] | None

    ip_address: str | None
    user_agent: str | None
