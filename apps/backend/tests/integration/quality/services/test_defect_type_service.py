"""Defect type service integration tests against PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import NotFoundError

from app.domain.quality.exceptions import (
    DefectGroupArchivedError,
    DefectTypeArchivedError,
    DefectTypeCodeTakenError,
)
from app.domain.quality.schemas import DefectTypeCreate
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.quality.services import DefectGroupService, DefectTypeService
    from tests.integration.quality.conftest import CreateGroup, CreateType

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def test_create_type_returns_it_with_group(
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group("RF")

    defect_type = await create_type(group, "RF_LOW")

    assert (defect_type.code, defect_type.group.code) == ("RF_LOW", "RF")


async def test_type_code_is_unique_across_groups(
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    await create_type(await create_group("RF"), "LOW")

    with pytest.raises(DefectTypeCodeTakenError):
        await create_type(await create_group("PWR"), "LOW")


async def test_create_type_in_archived_group_is_rejected(
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group(archived=True)

    with pytest.raises(DefectGroupArchivedError):
        await create_type(group)


async def test_create_type_in_missing_group_is_not_found(
    session: AsyncSession,
    defect_type_service: DefectTypeService,
) -> None:
    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await defect_type_service.create_type(
                DefectTypeCreate(
                    group_id=uuid4(),
                    code="LOW",
                    name="Low",
                    description="Weak signal",
                ),
            )


async def test_update_type_changes_given_fields(
    session: AsyncSession,
    defect_type_service: DefectTypeService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    defect_type = await create_type(await create_group())

    async with unit_of_work(session):
        updated = await defect_type_service.update_type(defect_type.id, {"engineer_action": "Replace antenna"})

    assert (updated.description, updated.engineer_action) == ("Weak signal", "Replace antenna")


async def test_update_archived_type_is_rejected(
    session: AsyncSession,
    defect_type_service: DefectTypeService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    defect_type = await create_type(await create_group(), archived=True)

    with pytest.raises(DefectTypeArchivedError):
        async with unit_of_work(session):
            await defect_type_service.update_type(defect_type.id, {"name": "Renamed"})


async def test_restore_type_of_archived_group_is_rejected(
    session: AsyncSession,
    defect_group_service: DefectGroupService,
    defect_type_service: DefectTypeService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group()
    defect_type = await create_type(group, archived=True)

    async with unit_of_work(session):
        await defect_group_service.set_archived(group.id, archived=True)

    with pytest.raises(DefectGroupArchivedError):
        async with unit_of_work(session):
            await defect_type_service.set_archived(defect_type.id, archived=False)


async def test_restore_type_of_active_group_is_accepted(
    session: AsyncSession,
    defect_type_service: DefectTypeService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    defect_type = await create_type(await create_group(), archived=True)

    async with unit_of_work(session):
        restored = await defect_type_service.set_archived(defect_type.id, archived=False)

    assert restored.archived_at is None


async def test_delete_type_removes_it(
    session: AsyncSession,
    defect_type_service: DefectTypeService,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    defect_type = await create_type(await create_group())

    async with unit_of_work(session):
        await defect_type_service.delete_type(defect_type.id)

    assert await defect_type_service.get_one_or_none(id=defect_type.id) is None
