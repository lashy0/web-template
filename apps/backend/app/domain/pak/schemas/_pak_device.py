from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import msgspec

from app.db.enums import PakDeviceKind
from app.lib.schema import CamelizedBaseStruct

CODE_MAX_LENGTH = 128

PakCode = Annotated[
    str,
    msgspec.Meta(min_length=1, max_length=CODE_MAX_LENGTH, pattern="^[A-Za-z0-9][A-Za-z0-9._-]*$"),
]


class PakDevice(CamelizedBaseStruct):
    id: UUID
    code: str
    kind: PakDeviceKind
    oauth_client_id: str
    is_active: bool
    last_seen_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PakDeviceCreate(CamelizedBaseStruct):
    code: PakCode
    kind: PakDeviceKind
    is_active: bool = True


class PakDeviceUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Change a device's attributes; activity and archiving have their own endpoints."""

    code: PakCode | msgspec.UnsetType = msgspec.UNSET
    kind: PakDeviceKind | msgspec.UnsetType = msgspec.UNSET

    def __post_init__(self) -> None:
        if all(
            value is msgspec.UNSET
            for value in (
                self.code,
                self.kind,
            )
        ):
            raise ValueError("At least one field must be provided for update")


class PakAccessKey(CamelizedBaseStruct):
    access_key: str


class PakDeviceProvisioned(CamelizedBaseStruct):
    device: PakDevice
    access_key: str
