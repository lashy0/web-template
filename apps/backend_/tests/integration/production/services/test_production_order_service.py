"""Production order service integration tests against PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import NotFoundError

from app.domain.production.exceptions import ProductionOrderArchivedError
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import ProductionOrderService
    from tests.integration.production.conftest import CreateOrder

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def test_update_order_changes_given_fields(
    session: AsyncSession,
    production_order_service: ProductionOrderService,
    create_order: CreateOrder,
) -> None:
    order = await create_order("Before")

    async with unit_of_work(session):
        await production_order_service.update_order(order.id, {"description": "Details"})

    stored = await production_order_service.get(order.id)
    assert (stored.name, stored.description) == ("Before", "Details")


async def test_update_archived_order_is_rejected(
    session: AsyncSession,
    production_order_service: ProductionOrderService,
    create_order: CreateOrder,
) -> None:
    order = await create_order(archived=True)

    with pytest.raises(ProductionOrderArchivedError):
        async with unit_of_work(session):
            await production_order_service.update_order(order.id, {"name": "After"})


async def test_update_missing_order_is_not_found(
    session: AsyncSession,
    production_order_service: ProductionOrderService,
) -> None:
    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await production_order_service.update_order(uuid4(), {"name": "After"})


async def test_archive_again_keeps_original_archive_time(
    session: AsyncSession,
    production_order_service: ProductionOrderService,
    create_order: CreateOrder,
) -> None:
    order = await create_order(archived=True)
    archived_at = order.archived_at

    async with unit_of_work(session):
        await production_order_service.set_archived(order.id, archived=True)

    assert (await production_order_service.get(order.id)).archived_at == archived_at


async def test_restore_clears_archive_time(
    session: AsyncSession,
    production_order_service: ProductionOrderService,
    create_order: CreateOrder,
) -> None:
    order = await create_order(archived=True)

    async with unit_of_work(session):
        await production_order_service.set_archived(order.id, archived=False)

    assert (await production_order_service.get(order.id)).archived_at is None


async def test_delete_order_removes_it(
    session: AsyncSession,
    production_order_service: ProductionOrderService,
    create_order: CreateOrder,
) -> None:
    order = await create_order()

    async with unit_of_work(session):
        await production_order_service.delete_order(order.id)

    assert await production_order_service.get_one_or_none(id=order.id) is None


@pytest.mark.parametrize(
    ("archived", "expected"),
    [(None, {"Current", "Archived"}), (True, {"Archived"}), (False, {"Current"})],
    ids=["all", "archived", "current"],
)
async def test_list_orders_filters_by_archive_state(
    production_order_service: ProductionOrderService,
    create_order: CreateOrder,
    archived: bool | None,
    expected: set[str],
) -> None:
    await create_order("Current")
    await create_order("Archived", archived=True)

    orders, total = await production_order_service.list_orders(archived=archived)

    assert {order.name for order in orders} == expected
    assert total == len(expected)
