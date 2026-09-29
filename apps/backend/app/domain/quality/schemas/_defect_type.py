from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import msgspec

from app.domain.quality.schemas._common import (
    CODE_ALLOWED,
    TEXT_MAX_LENGTH,
    Text,
    Title,
    validate_code,
    validate_text,
    validate_title,
)
from app.lib.schema import CamelizedBaseStruct

CODE_MAX_LENGTH = 64

DefectTypeCode = Annotated[str, msgspec.Meta(min_length=1, max_length=CODE_MAX_LENGTH, pattern=CODE_ALLOWED)]
RequiredText = Annotated[str, msgspec.Meta(min_length=1, max_length=TEXT_MAX_LENGTH)]


class DefectTypeGroup(CamelizedBaseStruct):
    id: UUID
    code: str
    name: str
    archived_at: datetime | None


class DefectType(CamelizedBaseStruct):
    id: UUID
    group: DefectTypeGroup
    code: str
    name: str
    description: str
    possible_cause: str | None
    engineer_action: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DefectTypeCreate(CamelizedBaseStruct):
    """Register a defect type in an active group; ``code`` and the group cannot change later."""

    group_id: UUID
    code: DefectTypeCode
    name: Title
    description: RequiredText
    possible_cause: Text | None = None
    engineer_action: Text | None = None

    def __post_init__(self) -> None:
        self.code = validate_code(self.code, max_length=CODE_MAX_LENGTH)
        self.name = validate_title(self.name)
        self.description = validate_title(self.description, max_length=TEXT_MAX_LENGTH)

        if self.possible_cause is not None:
            self.possible_cause = validate_text(self.possible_cause)

        if self.engineer_action is not None:
            self.engineer_action = validate_text(self.engineer_action)


class DefectTypeUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Change a defect type's attributes; archiving has its own endpoints."""

    name: Title | msgspec.UnsetType = msgspec.UNSET
    description: RequiredText | msgspec.UnsetType = msgspec.UNSET
    possible_cause: Text | msgspec.UnsetType | None = msgspec.UNSET
    engineer_action: Text | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if all(
            value is msgspec.UNSET for value in (self.name, self.description, self.possible_cause, self.engineer_action)
        ):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = validate_title(self.name)

        if isinstance(self.description, str):
            self.description = validate_title(self.description, max_length=TEXT_MAX_LENGTH)

        if isinstance(self.possible_cause, str):
            self.possible_cause = validate_text(self.possible_cause)

        if isinstance(self.engineer_action, str):
            self.engineer_action = validate_text(self.engineer_action)
