from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

import msgspec

from app.domain.production.schemas._common import validate_title
from app.lib.lorawan import normalize_dev_eui_prefix
from app.lib.schema import CamelizedBaseStruct
from app.lib.validation import ValidationError

SHORT_CODE_MAX_LENGTH = 10
_SHORT_CODE_PATTERN = re.compile(r"[a-z0-9]+")


def _validate_short_code(value: str) -> str:
    short_code = value.strip().lower()

    if len(short_code) > SHORT_CODE_MAX_LENGTH or _SHORT_CODE_PATTERN.fullmatch(short_code) is None:
        msg = f"Short code must be 1 to {SHORT_CODE_MAX_LENGTH} Latin letters or digits"

        raise ValidationError(msg)

    return short_code


class KgPrefix(CamelizedBaseStruct):
    id: UUID
    prefix: str
    short_code: str
    name: str | None
    available_qty: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KgPrefixCreate(CamelizedBaseStruct):
    """Register a DevEUI prefix; ``prefix`` and ``short_code`` cannot change later."""

    prefix: str
    short_code: str
    name: str | None = None

    def __post_init__(self) -> None:
        self.prefix = normalize_dev_eui_prefix(self.prefix.strip())
        self.short_code = _validate_short_code(self.short_code)

        if self.name is not None:
            self.name = validate_title(self.name)


class KgPrefixUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Rename a DevEUI prefix; ``null`` clears the name."""

    name: str | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if self.name is msgspec.UNSET:
            msg = "At least one field must be provided for update"

            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = validate_title(self.name)
