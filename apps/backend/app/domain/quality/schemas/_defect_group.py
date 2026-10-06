from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import msgspec

from app.domain.quality.schemas._common import CODE_ALLOWED, Text, Title, validate_code, validate_text, validate_title
from app.lib.concurrency import VersionedUpdate
from app.lib.schema import CamelizedBaseStruct

CODE_MAX_LENGTH = 32

DefectGroupCode = Annotated[str, msgspec.Meta(min_length=1, max_length=CODE_MAX_LENGTH, pattern=CODE_ALLOWED)]


class DefectGroup(CamelizedBaseStruct):
    id: UUID
    code: str
    name: str
    description: str | None
    types_count: int
    active_types_count: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DefectGroupCreate(CamelizedBaseStruct):
    """Register a defect group; ``code`` is what a PAK reports and cannot change later."""

    code: DefectGroupCode
    name: Title
    description: Text | None = None

    def __post_init__(self) -> None:
        self.code = validate_code(self.code, max_length=CODE_MAX_LENGTH)
        self.name = validate_title(self.name)

        if self.description is not None:
            self.description = validate_text(self.description)


class DefectGroupUpdate(VersionedUpdate, omit_defaults=True):
    """Change a defect group's attributes; archiving has its own endpoints."""

    name: Title | msgspec.UnsetType = msgspec.UNSET
    description: Text | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if self.name is msgspec.UNSET and self.description is msgspec.UNSET:
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = validate_title(self.name)

        if isinstance(self.description, str):
            self.description = validate_text(self.description)
