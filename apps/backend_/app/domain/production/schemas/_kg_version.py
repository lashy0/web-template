from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from app.domain.production.schemas._common import validate_description, validate_title
from app.lib.schema import CamelizedBaseStruct

CODE_MAX_LENGTH = 32


class KgVersion(CamelizedBaseStruct):
    id: UUID
    code: str
    name: str
    description: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KgVersionCreate(CamelizedBaseStruct):
    """Register a KG version; ``code`` cannot change later."""

    code: str
    name: str
    description: str | None = None

    def __post_init__(self) -> None:
        self.code = validate_title(self.code, max_length=CODE_MAX_LENGTH)
        self.name = validate_title(self.name)

        if self.description is not None:
            self.description = validate_description(self.description)


class KgVersionUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Change a KG version's attributes; archiving has its own endpoints."""

    name: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if self.name is msgspec.UNSET and self.description is msgspec.UNSET:
            msg = "At least one field must be provided for update"

            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = validate_title(self.name)

        if isinstance(self.description, str):
            self.description = validate_description(self.description)
