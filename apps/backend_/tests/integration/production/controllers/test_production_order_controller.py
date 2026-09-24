"""Production order routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db import models as m

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import CreateOrder

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _administrator(sign_in: SignIn) -> None:
    await sign_in()


async def test_list_production_orders_returns_page(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    await create_order("Order A")

    response = await client.get("/production-orders")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["Order A"]


async def test_list_production_orders_filters_archived(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    await create_order("Current")
    await create_order("Archived", archived=True)

    response = await client.get("/production-orders", params={"archived": "true"})

    assert [item["name"] for item in response.json()["items"]] == ["Archived"]


async def test_get_production_order_returns_it(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    order = await create_order("Order A")

    response = await client.get(f"/production-orders/{order.id}")

    assert (response.status_code, response.json()["id"]) == (200, str(order.id))


async def test_get_missing_production_order_is_not_found(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get(f"/production-orders/{UUID(int=0)}")

    assert response.status_code == 404


async def test_create_production_order_returns_created_order(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/production-orders", json={"name": "  Order A  ", "description": None})

    assert response.status_code == 201
    assert response.json()["name"] == "Order A"
    assert response.json()["archivedAt"] is None


async def test_create_production_order_with_blank_name_is_bad_request(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/production-orders", json={"name": "   "})

    assert response.status_code == 400


async def test_create_production_order_writes_audit_entry(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
) -> None:
    response = await client.post("/production-orders", json={"name": "Order A"})

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.target_id == response.json()["id"]))
    assert entry is not None
    assert (entry.action, entry.target_label) == ("production_order.created", "Order A")


async def test_update_production_order_changes_given_fields(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    order = await create_order("Order A")

    response = await client.patch(f"/production-orders/{order.id}", json={"description": "Details"})

    assert (response.status_code, response.json()["name"], response.json()["description"]) == (
        200,
        "Order A",
        "Details",
    )


async def test_update_archived_production_order_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    order = await create_order(archived=True)

    response = await client.patch(f"/production-orders/{order.id}", json={"name": "Renamed"})

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "production_order_archived"})


async def test_archive_production_order_sets_archive_time(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    order = await create_order()

    response = await client.post(f"/production-orders/{order.id}/archive")

    assert (response.status_code, response.json()["archivedAt"] is not None) == (200, True)


async def test_restore_production_order_clears_archive_time(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    order = await create_order(archived=True)

    response = await client.post(f"/production-orders/{order.id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_delete_production_order_removes_it(
    client: AsyncTestClient[Litestar],
    create_order: CreateOrder,
) -> None:
    order = await create_order()

    response = await client.delete(f"/production-orders/{order.id}")

    assert response.status_code == 204
    assert (await client.get(f"/production-orders/{order.id}")).status_code == 404
