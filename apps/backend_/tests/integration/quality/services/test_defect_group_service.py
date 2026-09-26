"""Defect group service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import NotFoundError

from app.domain.quality.exceptions import (
    DefectGroupArchivedError,
    DefectGroupCodeTakenError,
    DefectGroupHasActiveTypesError,
    DefectGroupInUseError,
)
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.quality.services import DefectGroupService, PakCheckService
    from tests.integration.quality.conftest import CreateGroup, CreatePak, CreateType

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def test_create_group_with_taken_code_is_rejected(create_group: CreateGroup) -> None:
    await create_group("RF")

    with pytest.raises(DefectGroupCodeTakenError):
        await create_group("RF")


async def test_new_group_has_no_types(create_group: CreateGroup) -> None:
    group = await create_group()

    assert (group.types_count, group.active_types_count) == (0, 0)


async def test_group_counts_its_active_and_archived_types(
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group()
    group_id = group.id
    await create_type(group, "RF_LOW")
    await create_type(group, "RF_NONE", archived=True)
    defect_group_service.repository.session.expire_all()

    stored = await defect_group_service.get(group_id)

    assert (stored.types_count, stored.active_types_count) == (2, 1)


async def test_update_group_changes_given_fields(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
) -> None:
    group = await create_group()

    async with unit_of_work(session):
        updated = await defect_group_service.update_group(group.id, {"description": "Radio faults"})

    assert (updated.name, updated.description) == ("Group RF", "Radio faults")


async def test_update_archived_group_is_rejected(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
) -> None:
    group = await create_group(archived=True)

    with pytest.raises(DefectGroupArchivedError):
        async with unit_of_work(session):
            await defect_group_service.update_group(group.id, {"name": "Renamed"})


async def test_update_missing_group_is_not_found(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
) -> None:
    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await defect_group_service.update_group(uuid4(), {"name": "Renamed"})


async def test_archive_group_with_active_type_is_rejected(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group()
    await create_type(group)

    with pytest.raises(DefectGroupHasActiveTypesError):
        async with unit_of_work(session):
            await defect_group_service.set_archived(group.id, archived=True)


async def test_archive_group_with_archived_types_is_accepted(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group()
    await create_type(group, archived=True)

    async with unit_of_work(session):
        archived = await defect_group_service.set_archived(group.id, archived=True)

    assert archived.archived_at is not None


async def test_archive_group_again_keeps_original_archive_time(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
) -> None:
    group = await create_group(archived=True)
    archived_at = group.archived_at

    async with unit_of_work(session):
        again = await defect_group_service.set_archived(group.id, archived=True)

    assert again.archived_at == archived_at


async def test_delete_group_without_types_removes_it(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
) -> None:
    group = await create_group()

    async with unit_of_work(session):
        await defect_group_service.delete_group(group.id)

    assert await defect_group_service.get_one_or_none(id=group.id) is None


async def test_delete_group_with_archived_type_is_rejected(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group()
    await create_type(group, archived=True)

    with pytest.raises(DefectGroupInUseError):
        async with unit_of_work(session):
            await defect_group_service.delete_group(group.id)


async def test_delete_group_referenced_by_a_pak_check_is_rejected(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    pak_check_service: PakCheckService,
    create_group: CreateGroup,
    create_pak: CreatePak,
) -> None:
    group = await create_group("RF")
    pak = await create_pak()

    async with unit_of_work(session):
        await pak_check_service.observe(
            pak=pak,
            name="rf_power",
            label="RF power",
            defect_group_code="RF",
            seen_at=datetime.now(UTC),
        )

    with pytest.raises(DefectGroupInUseError):
        async with unit_of_work(session):
            await defect_group_service.delete_group(group.id)
