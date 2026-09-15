from uuid import UUID

from .exceptions import (
    ProductionOrderArchivedError,
    ProductionOrderNotFoundError,
)
from .model import ProductionOrder
from .repository import ProductionOrderRepository


class ProductionOrderQueries:
    """Read API and production-internal eligibility lookup for orders."""

    def __init__(self, repository: ProductionOrderRepository) -> None:
        self._repository = repository

    async def get(self, order_id: UUID) -> ProductionOrder | None:
        return await self._repository.get(order_id)

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
        return await self._repository.search(
            q=q,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def totals(self, order_id: UUID) -> tuple[int, int]:
        return await self._repository.get_totals(order_id)

    async def ensure_assignable(self, order_id: UUID) -> ProductionOrder:
        item = await self._repository.get(order_id, for_update=True)
        if item is None:
            raise ProductionOrderNotFoundError
        if item.archived_at is not None:
            raise ProductionOrderArchivedError
        return item


async def required_order(
    repository: ProductionOrderRepository, order_id: UUID, *, for_update: bool = False
) -> ProductionOrder:
    item = await repository.get(order_id, for_update=for_update)
    if item is None:
        raise ProductionOrderNotFoundError
    return item
