from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m
from app.domain.production.exceptions import ProductionOrderArchivedError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from advanced_alchemy.filters import StatementFilter


class ProductionOrderService(service.SQLAlchemyAsyncRepositoryService[m.ProductionOrder]):
    """Application service for production orders."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.ProductionOrder]):
        """Production order SQLAlchemy repository."""

        model_type = m.ProductionOrder

    repository_type = Repo

    async def list_orders(
        self,
        *filters: StatementFilter,
        archived: bool | None = None,
    ) -> tuple[Sequence[m.ProductionOrder], int]:
        """List orders, optionally only archived (``True``) or only current (``False``) ones."""
        if archived is None:
            return await self.get_many_and_count(*filters)

        archived_at = m.ProductionOrder.archived_at
        state = archived_at.is_not(None) if archived else archived_at.is_(None)

        return await self.get_many_and_count(*filters, state)

    async def update_order(
        self,
        order_id: UUID,
        data: dict[str, object],
    ) -> m.ProductionOrder:
        order = await self._require(order_id, for_update=True)

        if order.archived_at is not None:
            raise ProductionOrderArchivedError

        return await self.update(
            data,
            item_id=order_id,
            auto_commit=False,
        )

    async def set_archived(
        self,
        order_id: UUID,
        *,
        archived: bool,
    ) -> m.ProductionOrder:
        """Archive or restore an order; repeating the request keeps the original archive time."""
        order = await self._require(order_id, for_update=True)

        if archived and order.archived_at is None:
            order.archived_at = datetime.now(UTC)
        elif not archived:
            order.archived_at = None

        await self.repository.session.flush()

        return order

    async def delete_order(self, order_id: UUID) -> m.ProductionOrder:
        order = await self._require(order_id, for_update=True)

        await self.repository.session.delete(order)
        await self.repository.session.flush()

        return order

    async def _require(
        self,
        order_id: UUID,
        *,
        for_update: bool = False,
    ) -> m.ProductionOrder:
        order = await self.get_one_or_none(
            m.ProductionOrder.id == order_id,
            with_for_update=for_update,
        )

        if order is None:
            raise NotFoundError("Production order not found.")

        return order
