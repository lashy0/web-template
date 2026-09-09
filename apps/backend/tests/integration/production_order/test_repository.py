from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.batch.models import Batch, BatchStatus
from app.modules.batch.repositories import BatchRepository
from app.modules.kg.models import KgDevEuiPrefix
from app.modules.production_order.models import ProductionOrder
from app.modules.production_order.repository import ProductionOrderRepository

pytestmark = pytest.mark.integration


async def test_search_totals_pagination_sorting_and_batch_filters(db_session):
    session = db_session
    key = uuid4().hex
    first = ProductionOrder(name=f"{key}-A", description="needle")
    second = ProductionOrder(name=f"{key}-B", description="needle")
    archived = ProductionOrder(name=f"{key}-C", archived_at=datetime.now(UTC))
    prefix = uuid4().hex[:10]
    session.add_all([first, second, archived, KgDevEuiPrefix(prefix=prefix, short_code=prefix)])
    await session.flush()
    for qty, order_id, is_archived in [(2, first.id, False), (3, first.id, True), (1, None, False)]:
        session.add(
            Batch(
                name=key,
                planned_qty=qty,
                day_plan_qty=1,
                dev_eui_prefix=prefix,
                status=BatchStatus.IN_PRODUCTION,
                production_order_id=order_id,
                archived_at=datetime.now(UTC) if is_archived else None,
            )
        )
    await session.flush()
    repo = ProductionOrderRepository(session)
    for sort in (
        "name",
        "created_at",
        "updated_at",
        "archived_at",
        "batches_count",
        "total_planned_qty",
    ):
        items, total = await repo.search(
            q=key, archived=False, page=1, page_size=25, sort=sort, order="asc"
        )
        assert total == 2
        assert {item.id for item, _, _ in items} == {first.id, second.id}
    items, total = await repo.search(
        q=key, archived=False, page=1, page_size=1, sort="total_planned_qty", order="desc"
    )
    assert total == 2
    assert [(item.id, count, qty) for item, count, qty in items] == [(first.id, 2, 5)]
    items, _ = await repo.search(
        q=key, archived=False, page=2, page_size=1, sort="total_planned_qty", order="desc"
    )
    assert [(item.id, count, qty) for item, count, qty in items] == [(second.id, 0, 0)]
    items, _ = await repo.search(
        q=key, archived=True, page=1, page_size=25, sort="name", order="asc"
    )
    assert [item.id for item, _, _ in items] == [archived.id]
    items, _ = await repo.search(
        q="needle", archived=False, page=1, page_size=100, sort="name", order="asc"
    )
    assert {first.id, second.id} <= {item.id for item, _, _ in items}
    batches = BatchRepository(session)
    for archived_filter in (False, True):
        items, total = await batches.search(
            q=key,
            status=None,
            archived=archived_filter,
            page=1,
            page_size=25,
            sort="name",
            order="asc",
            production_order_id=first.id,
        )
        assert total == 1
        assert items[0].production_order.id == first.id
    items, total = await batches.search(
        q=key,
        status=None,
        archived=False,
        page=1,
        page_size=25,
        sort="name",
        order="asc",
        without_production_order=True,
    )
    assert total == 1
    assert items[0].production_order_id is None
