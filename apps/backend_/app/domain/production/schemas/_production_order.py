from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from app.lib.schema import CamelizedBaseStruct
from app.lib.validation import validate_length, validate_not_empty

NAME_MAX_LENGTH = 128
DESCRIPTION_MAX_LENGTH = 2000


def _validate_name(value: str) -> str:
    return validate_length(validate_not_empty(value), max_length=NAME_MAX_LENGTH)


def _validate_description(value: str) -> str:
    return validate_length(value, max_length=DESCRIPTION_MAX_LENGTH)


class ProductionOrder(CamelizedBaseStruct):
    id: UUID
    name: str
    description: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProductionOrderCreate(CamelizedBaseStruct):
    name: str
    description: str | None = None

    def __post_init__(self) -> None:
        self.name = _validate_name(self.name)

        if self.description is not None:
            self.description = _validate_description(self.description)


class ProductionOrderUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Change an order's attributes; archiving has its own endpoints."""

    name: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if self.name is msgspec.UNSET and self.description is msgspec.UNSET:
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = _validate_name(self.name)

        if isinstance(self.description, str):
            self.description = _validate_description(self.description)
