from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.db.enums import KgOtkStatus, KgState
from app.lib.schema import CamelizedBaseStruct


class PackingBlocker(StrEnum):
    """Why a KG unit cannot be packed; each value is the error code packing answers with."""

    ALREADY_PACKED = "packing_kg_already_packed"
    SCRAPPED = "packing_kg_scrapped"
    BATCH_ARCHIVED = "packing_batch_archived"
    OTK_IN_PROGRESS = "packing_otk_in_progress"
    OTK_NOT_PASSED = "packing_otk_not_passed"


class PackingUnitBatch(CamelizedBaseStruct):
    id: UUID
    name: str
    join_eui: str


class PackingUnit(CamelizedBaseStruct):
    """A KG unit as the packing workstation sees it: what goes on the label and whether it may be packed."""

    dev_eui: str
    short_id: str
    state: KgState
    otk_status: KgOtkStatus
    last_verification_at: datetime | None
    packed_at: datetime | None
    batch: PackingUnitBatch
    can_pack: bool
    blocked_by: PackingBlocker | None
    """The first rule that forbids packing; ``None`` when ``can_pack`` is true."""
