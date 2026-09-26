from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import msgspec

from app.db.enums import BatchStatus
from app.domain.production.schemas._common import validate_description, validate_title
from app.lib.lorawan import ActivationType, LoRaWanVersion
from app.lib.schema import CamelizedBaseStruct

# No upper bound of its own: the free DevEUIs of the prefix limit a batch.
PlannedQty = Annotated[int, msgspec.Meta(ge=1, description="Number of KG units in the batch.")]
DayPlanQty = Annotated[int, msgspec.Meta(ge=1, description="Planned KG units per day.")]


class BatchKgPrefix(CamelizedBaseStruct):
    id: UUID
    prefix: str
    short_code: str
    name: str | None


class BatchKgVersion(CamelizedBaseStruct):
    id: UUID
    code: str
    name: str


class BatchProductionOrder(CamelizedBaseStruct):
    id: UUID
    name: str


class UserSummary(CamelizedBaseStruct):
    """The user who created a production record."""

    id: UUID
    name: str


class Batch(CamelizedBaseStruct):
    id: UUID
    name: str
    description: str | None
    planned_qty: int
    received_qty: int
    packed_qty: int
    day_plan_qty: int
    status: BatchStatus
    kg_prefix: BatchKgPrefix
    first_dev_eui: str
    last_dev_eui: str
    kg_version: BatchKgVersion | None
    production_order: BatchProductionOrder | None
    activation_type: ActivationType
    lorawan_version: LoRaWanVersion
    join_eui: str
    created_by: UserSummary | None
    completed_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BatchCreate(CamelizedBaseStruct):
    """Create a batch and allocate its DevEUI range; the range and LoRaWAN settings never change."""

    name: str
    kg_prefix_id: UUID
    planned_qty: PlannedQty
    day_plan_qty: DayPlanQty
    activation_type: ActivationType
    lorawan_version: LoRaWanVersion
    description: str | None = None
    kg_version_id: UUID | None = None
    production_order_id: UUID | None = None

    def __post_init__(self) -> None:
        self.name = validate_title(self.name)

        if self.description is not None:
            self.description = validate_description(self.description)


class BatchUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Change a batch's attributes; the production order and archiving have their own endpoints."""

    name: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType | None = msgspec.UNSET
    day_plan_qty: DayPlanQty | msgspec.UnsetType = msgspec.UNSET

    def __post_init__(self) -> None:
        if all(field is msgspec.UNSET for field in (self.name, self.description, self.day_plan_qty)):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = validate_title(self.name)

        if isinstance(self.description, str):
            self.description = validate_description(self.description)


class BatchProductionOrderAssignment(CamelizedBaseStruct):
    """Assign the batch to a production order, or detach it with ``null``."""

    production_order_id: UUID | None


class DevEuiRange(CamelizedBaseStruct):
    first_dev_eui: str
    last_dev_eui: str
