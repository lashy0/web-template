"""DevEUI prefix service integration tests against PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import NotFoundError

from app.domain.production.exceptions import (
    KgPrefixArchivedError,
    KgPrefixInUseError,
    KgPrefixShortCodeTakenError,
    KgPrefixTakenError,
)
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import KgPrefixService
    from tests.integration.production.conftest import CreateBatch, CreatePrefix

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def test_create_prefix_with_taken_prefix_is_rejected(create_prefix: CreatePrefix) -> None:
    await create_prefix("a1b2c3d4e5", "ab1")

    with pytest.raises(KgPrefixTakenError):
        await create_prefix("a1b2c3d4e5", "ab2")


async def test_create_prefix_with_taken_short_code_is_rejected(create_prefix: CreatePrefix) -> None:
    await create_prefix("a1b2c3d4e5", "ab1")

    with pytest.raises(KgPrefixShortCodeTakenError):
        await create_prefix("f0f0f0f0f0", "ab1")


async def test_update_prefix_renames_it(
    session: AsyncSession,
    kg_prefix_service: KgPrefixService,
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    async with unit_of_work(session):
        await kg_prefix_service.update_prefix(prefix.id, {"name": "Line A"})

    assert (await kg_prefix_service.get(prefix.id)).name == "Line A"


async def test_update_archived_prefix_is_rejected(
    session: AsyncSession,
    kg_prefix_service: KgPrefixService,
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix(archived=True)

    with pytest.raises(KgPrefixArchivedError):
        async with unit_of_work(session):
            await kg_prefix_service.update_prefix(prefix.id, {"name": "Line A"})


async def test_update_missing_prefix_is_not_found(
    session: AsyncSession,
    kg_prefix_service: KgPrefixService,
) -> None:
    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await kg_prefix_service.update_prefix(uuid4(), {"name": "Line A"})


async def test_archive_prefix_again_keeps_original_archive_time(
    session: AsyncSession,
    kg_prefix_service: KgPrefixService,
    create_prefix: CreatePrefix,
) -> None:
    item = await create_prefix(archived=True)
    archived_at = item.archived_at

    async with unit_of_work(session):
        await kg_prefix_service.set_archived(item.id, archived=True)

    assert (await kg_prefix_service.get(item.id)).archived_at == archived_at


async def test_delete_prefix_with_allocated_dev_euis_is_rejected(
    session: AsyncSession,
    kg_prefix_service: KgPrefixService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    with pytest.raises(KgPrefixInUseError):
        async with unit_of_work(session):
            await kg_prefix_service.delete_prefix(batch.kg_prefix_id)
