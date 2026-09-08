from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .common import DevEuiPrefix


class CreateKgDevEuiPrefixRequest(BaseModel):
    prefix: DevEuiPrefix
    short_code: str = Field(
        min_length=1,
        max_length=10,
        pattern=r"^[a-zA-Z0-9]+$",
    )
    name: str | None = Field(default=None, max_length=128)

    @field_validator("short_code", mode="before")
    @classmethod
    def normalize_short_code(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()

        return value


class UpdateKgDevEuiPrefixRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)


class KgDevEuiPrefixResponse(BaseModel):
    prefix: DevEuiPrefix
    short_code: str
    name: str | None
    batch_count: int = Field(ge=0)
    created_at: datetime
    archived_at: datetime | None


class KgDevEuiPrefixSummaryResponse(BaseModel):
    prefix: DevEuiPrefix
    short_code: str
    name: str | None


class KgDevEuiPrefixListResponse(BaseModel):
    items: list[KgDevEuiPrefixResponse]
    total: int
    page: int
    page_size: int


class UpdateKgDevEuiPrefixArchivedRequest(BaseModel):
    archived: bool
