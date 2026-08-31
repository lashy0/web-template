import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, field_validator

from app.modules.kg.models import KgStatus

DEV_EUI_PATTERN = re.compile(r"^[0-9a-f]{16}$")
DEV_EUI_PREFIX_PATTERN = re.compile(r"^[0-9a-f]{10}$")


def normalize_dev_eui(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("DevEUI must be a string")

    value = value.strip().lower()

    if not DEV_EUI_PATTERN.fullmatch(value):
        raise ValueError("DevEUI must contain exactly 16 hex characters")

    return value


def normalize_dev_eui_prefix(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(
            "DevEUI prefix must be a string"
        )

    value = value.strip().lower()

    if not DEV_EUI_PREFIX_PATTERN.fullmatch(value):
        raise ValueError(
            "DevEUI prefix must contain exactly 10 hex characters"
        )

    return value


DevEui = Annotated[str, BeforeValidator(normalize_dev_eui)]

DevEuiPrefix = Annotated[str, BeforeValidator(normalize_dev_eui_prefix)]


class KgResponse(BaseModel):
    dev_eui: DevEui
    short_id: str
    batch_id: UUID
    status: KgStatus
    created_at: datetime
    updated_at: datetime


class KgListResponse(BaseModel):
    items: list[KgResponse]
    total: int
    page: int
    page_size: int


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
    created_at: datetime


class KgDevEuiPrefixListResponse(BaseModel):
    items: list[KgDevEuiPrefixResponse]
    total: int
