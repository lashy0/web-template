"""Compatibility-facing composition for the migrated order commands and queries."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from .commands import (
    CreateProductionOrder,
    DeleteProductionOrder,
    SetProductionOrderArchived,
    UpdateProductionOrder,
)
from .exceptions import ProductionOrderConflictError
from .model import ProductionOrder
from .queries import ProductionOrderQueries
from .repository import ProductionOrderRepository


@asynccontextmanager
async def _transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    try:
        async with session_factory() as session, session.begin():
            yield session
    except IntegrityError as exc:
        raise ProductionOrderConflictError from exc


class ProductionOrderService:
    """Caller-UoW facade retained for legacy in-process consumers."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = ProductionOrderRepository(session)
        self._audit = TransactionalAuditWriter.from_session(session)

    async def get(self, order_id: UUID) -> ProductionOrder | None:
        return await ProductionOrderQueries(self._repository).get(order_id)

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
        return await ProductionOrderQueries(self._repository).list(
            q=q,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def get_totals(self, order_id: UUID) -> tuple[int, int]:
        return await ProductionOrderQueries(self._repository).totals(order_id)

    async def assign(self, order_id: UUID) -> ProductionOrder:
        return await ProductionOrderQueries(self._repository).ensure_assignable(order_id)

    async def create(
        self, *, actor: CurrentPrincipal, name: str, description: str | None
    ) -> ProductionOrder:
        return await CreateProductionOrder(self._repository, self._audit).execute(
            actor=actor, name=name, description=description
        )

    async def update(
        self, order_id: UUID, *, actor: CurrentPrincipal, updates: Mapping[str, object]
    ) -> ProductionOrder:
        return await UpdateProductionOrder(self._repository, self._audit).execute(
            actor=actor, order_id=order_id, updates=updates
        )

    async def set_archived(
        self, order_id: UUID, *, actor: CurrentPrincipal, archived: bool
    ) -> ProductionOrder:
        return await SetProductionOrderArchived(self._repository, self._audit).execute(
            actor=actor, order_id=order_id, archived=archived
        )

    async def delete(self, order_id: UUID, *, actor: CurrentPrincipal) -> None:
        await DeleteProductionOrder(self._repository, self._audit).execute(
            actor=actor, order_id=order_id
        )
