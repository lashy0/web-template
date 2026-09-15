"""Deprecated import compatibility for pre-context in-process callers."""

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.production.production_orders.model import ProductionOrder
from app.contexts.production.production_orders.service import ProductionOrderService, _transaction
from app.shared.security import CurrentPrincipal


class ProductionOrderManagementService:
    """Legacy transaction runner; application presentation does not use it."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, order_id: UUID) -> ProductionOrder | None:
        async with self._session_factory() as session:
            return await ProductionOrderService(session).get(order_id)

    async def list(self, **kwargs: object) -> tuple[list[tuple[ProductionOrder, int, int]], int]:
        async with self._session_factory() as session:
            return await ProductionOrderService(session).list(**kwargs)  # type: ignore[arg-type]

    async def get_totals(self, order_id: UUID) -> tuple[int, int]:
        async with self._session_factory() as session:
            return await ProductionOrderService(session).get_totals(order_id)

    async def create(
        self, *, actor: CurrentPrincipal, name: str, description: str | None
    ) -> ProductionOrder:
        async with _transaction(self._session_factory) as session:
            return await ProductionOrderService(session).create(
                actor=actor, name=name, description=description
            )

    async def update(
        self, *, actor: CurrentPrincipal, order_id: UUID, updates: Mapping[str, object]
    ) -> ProductionOrder:
        async with _transaction(self._session_factory) as session:
            return await ProductionOrderService(session).update(
                order_id, actor=actor, updates=updates
            )

    async def set_archived(
        self, *, actor: CurrentPrincipal, order_id: UUID, archived: bool
    ) -> ProductionOrder:
        async with _transaction(self._session_factory) as session:
            return await ProductionOrderService(session).set_archived(
                order_id, actor=actor, archived=archived
            )

    async def delete(self, *, actor: CurrentPrincipal, order_id: UUID) -> None:
        async with _transaction(self._session_factory) as session:
            await ProductionOrderService(session).delete(order_id, actor=actor)


__all__ = ["ProductionOrderManagementService"]
