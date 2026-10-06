from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import msgspec

from app.domain.production.schemas._common import Title, validate_title
from app.lib.concurrency import VersionedUpdate
from app.lib.lorawan import MULTICAST_GROUP_IDS
from app.lib.schema import CamelizedBaseStruct

DEFAULT_FREQUENCY_HZ = 869_100_000
"""The downlink frequency of the groups configured so far (RU864)."""

McGroupId = Annotated[
    int,
    msgspec.Meta(
        ge=min(MULTICAST_GROUP_IDS),
        le=max(MULTICAST_GROUP_IDS),
        description="McGroupID: the slot of the group in a KG unit.",
    ),
]
FrequencyHz = Annotated[
    int,
    msgspec.Meta(ge=100_000_000, le=1_000_000_000, description="Downlink frequency of the group, in Hz."),
]
Datarate = Annotated[int, msgspec.Meta(ge=0, le=15, description="Downlink data rate of the group (DR).")]


class MulticastGroup(CamelizedBaseStruct):
    id: UUID
    name: str
    group_id: int
    mc_addr: str
    frequency_hz: int
    datarate: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MulticastGroupKeys(CamelizedBaseStruct):
    """The McKey of a group and the session keys derived from it; hex values are lower case."""

    mc_key: str
    mc_nwk_s_key: str
    mc_app_s_key: str


class MulticastGroupCreate(CamelizedBaseStruct):
    """Register a multicast group; the server generates its address and McKey."""

    name: Title
    group_id: McGroupId
    frequency_hz: FrequencyHz = DEFAULT_FREQUENCY_HZ
    datarate: Datarate = 0

    def __post_init__(self) -> None:
        self.name = validate_title(self.name)


class MulticastGroupUpdate(VersionedUpdate, omit_defaults=True):
    """Change a multicast group; only the name changes once batches use it."""

    name: Title | msgspec.UnsetType = msgspec.UNSET
    group_id: McGroupId | msgspec.UnsetType = msgspec.UNSET
    frequency_hz: FrequencyHz | msgspec.UnsetType = msgspec.UNSET
    datarate: Datarate | msgspec.UnsetType = msgspec.UNSET

    def __post_init__(self) -> None:
        if all(field is msgspec.UNSET for field in (self.name, self.group_id, self.frequency_hz, self.datarate)):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.name, str):
            self.name = validate_title(self.name)
