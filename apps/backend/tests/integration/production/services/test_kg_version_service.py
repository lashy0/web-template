"""KG version service integration tests against PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import NotFoundError

from app.domain.production.exceptions import KgVersionArchivedError, KgVersionCodeTakenError, KgVersionInUseError
from app.domain.production.schemas import BatchCreate
from app.lib.lorawan import ActivationType, LoRaWanVersion
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import BatchService, KgVersionService
    from tests.integration.production.conftest import CreatePrefix, CreateVersion

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def test_create_version_with_taken_code_is_rejected(create_version: CreateVersion) -> None:
    await create_version("v1")

    with pytest.raises(KgVersionCodeTakenError):
        await create_version("v1")


async def test_update_version_changes_given_fields(
    session: AsyncSession,
    kg_version_service: KgVersionService,
    create_version: CreateVersion,
) -> None:
    version = await create_version("v1")

    async with unit_of_work(session):
        await kg_version_service.update_version(version.id, {"description": "Rev. B board"})

    stored = await kg_version_service.get(version.id)
    assert (stored.name, stored.description) == ("Version v1", "Rev. B board")


async def test_update_archived_version_is_rejected(
    session: AsyncSession,
    kg_version_service: KgVersionService,
    create_version: CreateVersion,
) -> None:
    version = await create_version(archived=True)

    with pytest.raises(KgVersionArchivedError):
        async with unit_of_work(session):
            await kg_version_service.update_version(version.id, {"name": "Renamed"})


async def test_update_missing_version_is_not_found(
    session: AsyncSession,
    kg_version_service: KgVersionService,
) -> None:
    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await kg_version_service.update_version(uuid4(), {"name": "Renamed"})


async def test_archive_version_again_keeps_original_archive_time(
    session: AsyncSession,
    kg_version_service: KgVersionService,
    create_version: CreateVersion,
) -> None:
    item = await create_version(archived=True)
    archived_at = item.archived_at

    async with unit_of_work(session):
        await kg_version_service.set_archived(item.id, archived=True)

    assert (await kg_version_service.get(item.id)).archived_at == archived_at


async def test_delete_version_used_by_batch_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    kg_version_service: KgVersionService,
    create_version: CreateVersion,
    create_prefix: CreatePrefix,
) -> None:
    version = await create_version()
    prefix = await create_prefix()

    async with unit_of_work(session):
        await batch_service.create_batch(
            BatchCreate(
                name="Batch",
                kg_prefix_id=prefix.id,
                planned_qty=1,
                day_plan_qty=1,
                activation_type=ActivationType.OTAA,
                lorawan_version=LoRaWanVersion.V1_0,
                kg_version_id=version.id,
            ),
            created_by_id=None,
        )

    with pytest.raises(KgVersionInUseError):
        async with unit_of_work(session):
            await kg_version_service.delete_version(version.id)
