from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal

from ..models import ProductionOrder
from .order import ProductionOrderService
from .transactions import transaction


class ProductionOrderManagementService:
    """API gateway owning sessions and transactions; delegates domain operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, order_id: UUID) -> ProductionOrder | None:
        async with self._session_factory() as session:
            return await ProductionOrderService(session).get(order_id)

    async def list(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[ProductionOrder, int, int]], int]:
        async with self._session_factory() as session:
            return await ProductionOrderService(session).list(
                q=q,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def get_totals(self, order_id: UUID) -> tuple[int, int]:
        async with self._session_factory() as session:
            return await ProductionOrderService(session).get_totals(order_id)

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        name: str,
        description: str | None,
    ) -> ProductionOrder:
        async with transaction(self._session_factory) as session:
            return await ProductionOrderService(session).create(
                actor=actor,
                name=name,
                description=description,
            )

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        order_id: UUID,
        updates: Mapping[str, object],
    ) -> ProductionOrder:
        async with transaction(self._session_factory) as session:
            return await ProductionOrderService(session).update(
                order_id,
                actor=actor,
                updates=updates,
            )

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        order_id: UUID,
        archived: bool,
    ) -> ProductionOrder:
        async with transaction(self._session_factory) as session:
            return await ProductionOrderService(session).set_archived(
                order_id,
                actor=actor,
                archived=archived,
            )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        order_id: UUID,
    ) -> None:
        async with transaction(self._session_factory) as session:
            await ProductionOrderService(session).delete(order_id, actor=actor)
