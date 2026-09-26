from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.db.enums import KgOtkStatus, KgState
from app.lib.lorawan import ActivationType, LoRaWanVersion
from app.lib.schema import CamelizedBaseStruct


class KgUnitBatch(CamelizedBaseStruct):
    id: UUID
    name: str


class KgUnit(CamelizedBaseStruct):
    dev_eui: str
    short_id: str
    state: KgState
    otk_status: KgOtkStatus
    last_verification_at: datetime | None
    activation_type: ActivationType
    lorawan_version: LoRaWanVersion
    batch: KgUnitBatch
    created_at: datetime
    updated_at: datetime
