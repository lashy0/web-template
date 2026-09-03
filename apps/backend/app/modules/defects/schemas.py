from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DefectGroupResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DefectGroupListItemResponse(DefectGroupResponse):
    active_types_count: int = Field(ge=0)
    types_count: int = Field(ge=0)


class DefectGroupListResponse(BaseModel):
    items: list[DefectGroupListItemResponse]
    total: int
    page: int
    page_size: int


class CreateDefectGroupRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32, pattern=r"^\S+$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("code", "name", mode="before")
    @classmethod
    def normalize_required_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value


class UpdateDefectGroupRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value


class UpdateDefectGroupArchivedRequest(BaseModel):
    archived: bool


class DefectGroupSummaryResponse(BaseModel):
    id: UUID
    code: str
    name: str
    archived_at: datetime | None


class DefectTypeResponse(BaseModel):
    id: UUID
    group_id: UUID
    group: DefectGroupSummaryResponse
    code: str
    name: str
    description: str
    possible_cause: str | None
    engineer_action: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DefectTypeListResponse(BaseModel):
    items: list[DefectTypeResponse]
    total: int
    page: int
    page_size: int


class CreateDefectTypeRequest(BaseModel):
    group_id: UUID
    code: str = Field(min_length=1, max_length=64, pattern=r"^\S+$")
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    possible_cause: str | None = Field(default=None, max_length=2000)
    engineer_action: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "code",
        "name",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_required_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "possible_cause",
        "engineer_action",
        mode="before",
    )
    @classmethod
    def normalize_optional_fields(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value


class UpdateDefectTypeRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    possible_cause: str | None = Field(default=None, max_length=2000)
    engineer_action: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "name",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_required_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "possible_cause",
        "engineer_action",
        mode="before",
    )
    @classmethod
    def normalize_optional_fields(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value


class UpdateDefectTypeArchivedRequest(BaseModel):
    archived: bool
