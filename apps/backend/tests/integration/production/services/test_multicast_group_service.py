"""Multicast group service integration tests against PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import update

from app.db import models as m
from app.domain.production.exceptions import (
    MulticastGroupArchivedError,
    MulticastGroupInUseError,
    MulticastGroupNameTakenError,
)
from app.domain.production.schemas import MulticastGroupKeys
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import MulticastGroupService
    from tests.integration.conftest import MulticastGroups
    from tests.integration.production.conftest import CreateBatch

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


def _group_data(name: str = "Group", group_id: int = 0) -> dict[str, object]:
    return {"name": name, "group_id": group_id, "frequency_hz": 869_100_000, "datarate": 0}


async def test_create_group_generates_address_and_key(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
) -> None:
    async with unit_of_work(session):
        group = await multicast_group_service.create_group(_group_data())

    assert (len(bytes.fromhex(group.mc_addr)), len(bytes.fromhex(group.mc_key))) == (4, 16)


async def test_create_group_with_taken_name_is_rejected(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
) -> None:
    with pytest.raises(MulticastGroupNameTakenError):
        async with unit_of_work(session):
            await multicast_group_service.create_group(_group_data(multicast_groups[0].name))


async def test_get_keys_derives_session_keys_from_the_stored_key(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
) -> None:
    group = multicast_groups[0]

    async with unit_of_work(session):
        await session.execute(
            update(m.MulticastGroup)
            .where(m.MulticastGroup.id == group.id)
            .values(mc_addr="5ef184c9", mc_key="43b650d61d8f9970df9b163ab6621b96")
        )

    keys = await multicast_group_service.get_keys(group.id)

    assert keys == MulticastGroupKeys(
        mc_key="43b650d61d8f9970df9b163ab6621b96",
        mc_nwk_s_key="6278651bc1c79abe26356d0f91065c37",
        mc_app_s_key="78e07423ffdd796b6057392e0a8278a1",
    )


async def test_update_group_used_by_batch_renames_it(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
    create_batch: CreateBatch,
) -> None:
    await create_batch()

    async with unit_of_work(session):
        group = await multicast_group_service.update_group(multicast_groups[0].id, {"name": "Renamed"})

    assert group.name == "Renamed"


async def test_update_radio_of_group_used_by_batch_is_rejected(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
    create_batch: CreateBatch,
) -> None:
    await create_batch()

    with pytest.raises(MulticastGroupInUseError):
        async with unit_of_work(session):
            await multicast_group_service.update_group(multicast_groups[0].id, {"frequency_hz": 868_900_000})


async def test_update_unused_group_changes_radio(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
) -> None:
    async with unit_of_work(session):
        group = await multicast_group_service.update_group(multicast_groups[0].id, {"datarate": 2})

    assert group.datarate == 2


async def test_update_group_to_taken_name_is_rejected(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
) -> None:
    with pytest.raises(MulticastGroupNameTakenError):
        async with unit_of_work(session):
            await multicast_group_service.update_group(multicast_groups[0].id, {"name": multicast_groups[1].name})


async def test_update_archived_group_is_rejected(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
) -> None:
    async with unit_of_work(session):
        await multicast_group_service.set_archived(multicast_groups[0].id, archived=True)

    with pytest.raises(MulticastGroupArchivedError):
        async with unit_of_work(session):
            await multicast_group_service.update_group(multicast_groups[0].id, {"name": "Renamed"})


async def test_delete_group_used_by_batch_is_rejected(
    session: AsyncSession,
    multicast_group_service: MulticastGroupService,
    multicast_groups: MulticastGroups,
    create_batch: CreateBatch,
) -> None:
    await create_batch()

    with pytest.raises(MulticastGroupInUseError):
        async with unit_of_work(session):
            await multicast_group_service.delete_group(multicast_groups[1].id)
