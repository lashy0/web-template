import asyncio
from uuid import uuid4

import pytest

from app.modules.kg.exceptions import KgDevEuiPrefixConflictError, KgDevEuiPrefixInUseError
from app.modules.kg.repositories import KgRepository
from app.modules.kg.services import KgDevEuiPrefixManagementService
from tests.integration.batch.test_lifecycle import scenario as scenario

pytestmark = pytest.mark.integration


async def test_parallel_batch_allocations_have_disjoint_ranges(scenario):
    factory, actor, batches, batch, _ = scenario

    async def allocate():
        return await batches.create(
            actor=actor,
            name=f"allocation-{uuid4()}",
            description=None,
            dev_eui_prefix=batch.dev_eui_prefix,
            planned_qty=2,
            day_plan_qty=1,
        )

    first, second = await asyncio.gather(allocate(), allocate())
    async with factory() as session:
        left = await KgRepository(session).list_by_batch(first.id)
        right = await KgRepository(session).list_by_batch(second.id)
    assert len(left) == len(right) == 2
    assert len({item.dev_eui for item in left + right}) == 4
    assert sorted(item.dev_eui for item in left + right) == [
        f"{batch.dev_eui_prefix}{suffix:06x}" for suffix in range(2, 6)
    ]


async def test_prefix_crud_and_in_use_guard(scenario):
    factory, actor, batches, _, _ = scenario
    service = KgDevEuiPrefixManagementService(factory)
    prefix = uuid4().hex[:10]
    item = await service.create(actor=actor, prefix=prefix, short_code=prefix, name="before")
    changed = await service.update(actor=actor, prefix=item.prefix, updates={"name": "after"})
    assert changed.name == "after"
    with pytest.raises(KgDevEuiPrefixConflictError):
        await service.create(actor=actor, prefix=uuid4().hex[:10], short_code=prefix, name=None)
    await service.delete(actor=actor, prefix=prefix)
    items, total = await service.list(
        q=prefix, archived=False, page=1, page_size=25, sort="prefix", order="asc"
    )
    assert total == 0
    assert items == []
    await service.create(actor=actor, prefix=prefix, short_code=prefix, name=None)
    await batches.create(
        actor=actor,
        name=f"prefix-use-{uuid4()}",
        description=None,
        dev_eui_prefix=prefix,
        planned_qty=1,
        day_plan_qty=1,
    )
    with pytest.raises(KgDevEuiPrefixInUseError):
        await service.delete(actor=actor, prefix=prefix)
