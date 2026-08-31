from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch.models import Batch, BatchStatus
from app.modules.kg.models import KgStatus
from app.modules.kg.repository import KgRepository


async def _batch(session: AsyncSession) -> Batch:
    batch = Batch(
        id=uuid4(),
        name="August production batch",
        description=None,
        planned_qty=100,
        day_plan_qty=20,
        status=BatchStatus.IN_PRODUCTION,
        created_by_user_id=None,
    )
    session.add(batch)
    await session.flush()
    return batch


@pytest.mark.integration
async def test_kg_can_be_created_and_retrieved_by_dev_eui(db_session: AsyncSession) -> None:
    batch = await _batch(db_session)
    repository = KgRepository(db_session)

    created = await repository.create(dev_eui="a1b2c3d4e5f60708", batch_id=batch.id)
    retrieved = await repository.get_by_dev_eui(created.dev_eui)

    assert retrieved is not None
    assert retrieved.dev_eui == created.dev_eui
    assert retrieved.batch_id == batch.id
    assert retrieved.status is KgStatus.REGISTERED
    assert retrieved.created_at.tzinfo is not None
    assert retrieved.updated_at.tzinfo is not None


@pytest.mark.integration
async def test_kg_search_applies_filters_sorting_and_pagination(db_session: AsyncSession) -> None:
    first_batch = await _batch(db_session)
    second_batch = await _batch(db_session)
    repository = KgRepository(db_session)
    await repository.create_many(
        dev_euis=["a1b2c3d4e5f60708", "b1b2c3d4e5f60708"],
        batch_id=first_batch.id,
    )
    second = await repository.create(dev_eui="c1b2c3d4e5f60708", batch_id=second_batch.id)
    await repository.update_status(second, status=KgStatus.TESTING)

    items, total = await repository.search(
        q="b2c3",
        batch_id=first_batch.id,
        status=KgStatus.REGISTERED,
        page=1,
        page_size=1,
        sort="dev_eui",
        order="asc",
    )

    assert total == 2
    assert [item.dev_eui for item in items] == ["a1b2c3d4e5f60708"]


@pytest.mark.integration
async def test_kg_bulk_operations_and_status_guard_are_scoped_to_batch(
    db_session: AsyncSession,
) -> None:
    first_batch = await _batch(db_session)
    second_batch = await _batch(db_session)
    repository = KgRepository(db_session)
    first, second = await repository.create_many(
        dev_euis=["a1b2c3d4e5f60708", "b1b2c3d4e5f60708"],
        batch_id=first_batch.id,
    )
    unrelated = await repository.create(dev_eui="c1b2c3d4e5f60708", batch_id=second_batch.id)

    assert not await repository.has_non_registered_by_batch(first_batch.id)
    await repository.update_status_many([first], status=KgStatus.PACKED)
    assert await repository.has_non_registered_by_batch(first_batch.id)
    assert not await repository.has_non_registered_by_batch(second_batch.id)

    selected = await repository.get_many_by_dev_euis([second.dev_eui, unrelated.dev_eui])
    assert {item.dev_eui for item in selected} == {second.dev_eui, unrelated.dev_eui}

    await repository.delete_by_batch(first_batch.id)
    assert await repository.get_by_dev_eui(first.dev_eui) is None
    assert await repository.get_by_dev_eui(second.dev_eui) is None
    assert await repository.get_by_dev_eui(unrelated.dev_eui) is not None
