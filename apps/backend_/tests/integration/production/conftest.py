"""Production domain integration test fixtures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import pytest

from app.domain.production.services import ProductionOrderService
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import models as m


pytestmark = pytest.mark.anyio

type CreateOrder = Callable[..., Awaitable[m.ProductionOrder]]


@pytest.fixture
async def production_order_service(session: AsyncSession) -> AsyncGenerator[ProductionOrderService]:
    """Create ProductionOrderService instance with the test session."""
    async with ProductionOrderService.new(session) as service:
        yield service


@pytest.fixture
def create_order(session: AsyncSession, production_order_service: ProductionOrderService) -> CreateOrder:
    """Return a helper that commits a production order, archived when requested."""

    async def _create(name: str = "Order", *, archived: bool = False) -> m.ProductionOrder:
        async with unit_of_work(session):
            order = await production_order_service.create({"name": name}, auto_commit=False)

            if archived:
                order = await production_order_service.set_archived(order.id, archived=True)

        return order

    return _create
