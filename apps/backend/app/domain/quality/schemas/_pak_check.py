from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.lib.schema import CamelizedBaseStruct


class PakCheckDefectGroup(CamelizedBaseStruct):
    id: UUID
    code: str
    name: str
    archived_at: datetime | None


class PakCheck(CamelizedBaseStruct):
    """A check as PAKs last reported it, identified by ``name`` and ``label`` together.

    ``misconfigured`` means the reported ``defectGroupCode`` matched no active
    defect group: create or restore the group, or fix the PAK configuration.
    """

    id: UUID
    name: str
    label: str
    defect_group_code: str
    defect_group: PakCheckDefectGroup | None
    misconfigured: bool
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime
