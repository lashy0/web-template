from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from app.domain.production.schemas._common import Description, Title, validate_description, validate_title
from app.lib.concurrency import VersionedUpdate
from app.lib.schema import CamelizedBaseStruct


class ProductionOrder(CamelizedBaseStruct):
    id: UUID
    name: str
    description: str | None
    batches_count: int
    total_planned_qty: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProductionOrderCreate(CamelizedBaseStruct):
    name: Title
    description: Description | None = None

    def __post_init__(self) -> None:
        self.name = validate_title(self.name)

        if self.description is not None:
            self.description = validate_description(self.description)


class ProductionOrderUpdate(VersionedUpdate, omit_defaults=True):
    """Change an order's attributes; archiving has its own endpoints."""

    name: Title | msgspec.UnsetType = msgspec.UNSET
    description: Description | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if self.name is msgspec.UNSET and self.description is msgspec.UNSET:
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = validate_title(self.name)

        if isinstance(self.description, str):
            self.description = validate_description(self.description)
