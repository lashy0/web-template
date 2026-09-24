"""Batch routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from sqlalchemy import select, update

from app.db import models as m
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import CreateBatch, CreateOrder, CreatePrefix

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(name="administrator", autouse=True)
async def fx_administrator(sign_in: SignIn) -> m.User:
    return await sign_in()


def _create_body(prefix_id: UUID, **overrides: object) -> dict[str, object]:
    return {
        "name": "Batch A",
        "kgPrefixId": str(prefix_id),
        "plannedQty": 3,
        "dayPlanQty": 3,
        "activationType": "otaa",
        "lorawanVersion": "1.0",
        **overrides,
    }


async def test_list_batches_returns_page(client: AsyncTestClient[Litestar], create_batch: CreateBatch) -> None:
    batch = await create_batch()

    response = await client.get("/batches")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(batch.id)]


async def test_list_batches_filters_by_status(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix()
    await create_batch(prefix)
    completed = await create_batch(prefix)
    await client.post(f"/batches/{completed.id}/complete")

    response = await client.get("/batches", params={"statusIn": "completed"})

    assert [item["id"] for item in response.json()["items"]] == [str(completed.id)]


async def test_list_batches_filters_by_production_order_presence(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
    create_order: CreateOrder,
) -> None:
    prefix = await create_prefix()
    order = await create_order()
    await create_batch(prefix, production_order_id=order.id)
    unassigned = await create_batch(prefix)

    response = await client.get("/batches", params={"hasProductionOrder": "false"})

    assert [item["id"] for item in response.json()["items"]] == [str(unassigned.id)]


async def test_get_batch_returns_it(client: AsyncTestClient[Litestar], create_batch: CreateBatch) -> None:
    batch = await create_batch()

    response = await client.get(f"/batches/{batch.id}")

    assert (response.status_code, response.json()["firstDevEui"]) == (200, batch.first_dev_eui)


async def test_get_missing_batch_is_not_found(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get(f"/batches/{UUID(int=0)}")

    assert response.status_code == 404


async def test_preview_dev_eui_range_shows_next_range(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5")

    response = await client.get(
        "/batches/dev-eui-range-preview",
        params={"kgPrefixId": str(prefix.id), "plannedQty": 16},
    )

    assert response.json() == {"firstDevEui": "a1b2c3d4e5000001", "lastDevEui": "a1b2c3d4e5000010"}


async def test_create_batch_returns_created_batch(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
    administrator: m.User,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5")

    response = await client.post("/batches", json=_create_body(prefix.id))

    assert response.status_code == 201
    body = response.json()
    assert (body["firstDevEui"], body["lastDevEui"], body["status"], body["createdBy"]["id"]) == (
        "a1b2c3d4e5000001",
        "a1b2c3d4e5000003",
        "in_production",
        str(administrator.id),
    )


async def test_create_batch_without_units_is_bad_request(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    response = await client.post("/batches", json=_create_body(prefix.id, plannedQty=0))

    assert response.status_code == 400


async def test_create_batch_writes_audit_entry(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    response = await client.post("/batches", json=_create_body(prefix.id))

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.target_id == response.json()["id"]))
    assert entry is not None
    assert entry.action == "batch.created"


async def test_update_batch_changes_given_fields(client: AsyncTestClient[Litestar], create_batch: CreateBatch) -> None:
    batch = await create_batch()

    response = await client.patch(f"/batches/{batch.id}", json={"dayPlanQty": 1})

    assert (response.status_code, response.json()["name"], response.json()["dayPlanQty"]) == (200, "Batch", 1)


async def test_update_batch_after_edit_window_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await session.execute(
            update(m.Batch).where(m.Batch.id == batch.id).values(created_at=datetime.now(UTC) - timedelta(hours=2))
        )

    response = await client.patch(f"/batches/{batch.id}", json={"name": "Renamed"})

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_edit_window_expired"})


async def test_assign_production_order_links_order(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_order: CreateOrder,
) -> None:
    batch = await create_batch()
    order = await create_order("Order A")

    response = await client.put(f"/batches/{batch.id}/production-order", json={"productionOrderId": str(order.id)})

    assert response.json()["productionOrder"] == {"id": str(order.id), "name": "Order A"}


async def test_detach_production_order_clears_it(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_order: CreateOrder,
) -> None:
    order = await create_order()
    batch = await create_batch(production_order_id=order.id)

    response = await client.put(f"/batches/{batch.id}/production-order", json={"productionOrderId": None})

    assert response.json()["productionOrder"] is None


async def test_complete_batch_completes_it(client: AsyncTestClient[Litestar], create_batch: CreateBatch) -> None:
    batch = await create_batch()

    response = await client.post(f"/batches/{batch.id}/complete")

    assert (response.status_code, response.json()["status"]) == (200, "completed")


async def test_archive_batch_archives_it(client: AsyncTestClient[Litestar], create_batch: CreateBatch) -> None:
    batch = await create_batch()

    response = await client.post(f"/batches/{batch.id}/archive")

    assert (response.status_code, response.json()["archivedAt"] is not None) == (200, True)


async def test_restore_batch_restores_it(client: AsyncTestClient[Litestar], create_batch: CreateBatch) -> None:
    batch = await create_batch(archived=True)

    response = await client.post(f"/batches/{batch.id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_delete_batch_removes_it(client: AsyncTestClient[Litestar], create_batch: CreateBatch) -> None:
    batch = await create_batch()

    response = await client.delete(f"/batches/{batch.id}")

    assert (response.status_code, (await client.get(f"/batches/{batch.id}")).status_code) == (204, 404)
