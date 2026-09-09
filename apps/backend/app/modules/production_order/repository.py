from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch.models import Batch

from .models import ProductionOrder


class ProductionOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        order_id: UUID,
        *,
        for_update: bool = False,
    ) -> ProductionOrder | None:
        return await self._session.get(
            ProductionOrder,
            order_id,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    @staticmethod
    def _query():
        totals = (
            select(
                Batch.production_order_id.label("order_id"),
                func.count(Batch.id).label("batches_count"),
                func.sum(Batch.planned_qty).label("total_planned_qty"),
            )
            .where(Batch.production_order_id.is_not(None))
            .group_by(Batch.production_order_id)
            .subquery()
        )
        count = func.coalesce(totals.c.batches_count, 0).label("batches_count")
        qty = func.coalesce(totals.c.total_planned_qty, 0).label("total_planned_qty")
        statement = select(ProductionOrder, count, qty).outerjoin(
            totals, totals.c.order_id == ProductionOrder.id
        )

        return statement, count, qty

    async def get_totals(self, order_id: UUID) -> tuple[int, int]:
        row = (
            await self._session.execute(
                select(
                    func.count(Batch.id),
                    func.coalesce(func.sum(Batch.planned_qty), 0),
                ).where(
                    Batch.production_order_id == order_id
                )
            )
        ).one()

        return int(row[0]), int(row[1])

    async def search(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[ProductionOrder, int, int]], int]:
        statement, count, qty = self._query()
        filters: list[ColumnElement[bool]] = [
            ProductionOrder.archived_at.is_not(None)
            if archived
            else ProductionOrder.archived_at.is_(None)
        ]

        if q and q.strip():
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    ProductionOrder.name.ilike(pattern),
                    ProductionOrder.description.ilike(pattern),
                )
            )

        columns = {
            field: getattr(ProductionOrder, field)
            for field in ("name", "created_at", "updated_at", "archived_at")
        }
        columns.update(batches_count=count, total_planned_qty=qty)
        column = columns[sort]
        ordered = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        rows = await self._session.execute(
            statement.where(*filters)
            .order_by(ordered, ProductionOrder.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = await self._session.scalar(
            select(func.count()).select_from(ProductionOrder).where(*filters)
        )

        return [(item, int(count), int(qty)) for item, count, qty in rows.tuples()], int(total or 0)

    async def contains_batches(self, order_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(Batch.production_order_id == order_id))
            )
        )

    async def create(
        self,
        *,
        name: str,
        description: str | None,
    ) -> ProductionOrder:
        item = ProductionOrder(
            name=name,
            description=description,
        )
        self._session.add(item)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def update_details(
        self,
        item: ProductionOrder,
        *,
        updates: Mapping[str, object],
    ) -> ProductionOrder:
        for field, value in updates.items():
            setattr(item, field, value)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def update_archived(
        self,
        item: ProductionOrder,
        *,
        archived_at: datetime | None,
    ) -> ProductionOrder:
        item.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def delete(self, item: ProductionOrder) -> None:
        await self._session.delete(item)
        await self._session.flush()
