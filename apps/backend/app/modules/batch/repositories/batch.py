from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Batch, BatchStatus


class BatchRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
        created_by_user_id: UUID | None,
    ) -> Batch:
        batch = Batch(
            name=name,
            description=description,
            dev_eui_prefix=dev_eui_prefix,
            planned_qty=planned_qty,
            day_plan_qty=day_plan_qty,
            status=BatchStatus.IN_PRODUCTION,
            created_by_user_id=created_by_user_id,
        )

        self._session.add(batch)

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def get_by_id(
        self,
        batch_id: UUID,
        *,
        for_update: bool = False,
    ) -> Batch | None:
        return await self._session.get(
            Batch,
            batch_id,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def update_details(
        self,
        batch: Batch,
        *,
        updates: Mapping[str, object],
    ) -> Batch:
        for field, value in updates.items():
            setattr(batch, field, value)

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def update_completed(
        self,
        batch: Batch,
        *,
        completed_at: datetime,
    ) -> Batch:
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = completed_at

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def update_archived(
        self,
        batch: Batch,
        *,
        archived_at: datetime | None,
    ) -> Batch:
        batch.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def delete(self, batch: Batch) -> None:
        await self._session.delete(batch)
        await self._session.flush()

    async def search(
        self,
        *,
        q: str | None,
        status: BatchStatus | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[Batch], int]:
        filters: list[ColumnElement[bool]] = [
            (Batch.archived_at.is_not(None) if archived else Batch.archived_at.is_(None))
        ]

        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    Batch.name.ilike(pattern),
                    Batch.description.ilike(pattern),
                )
            )

        if status is not None:
            filters.append(Batch.status == status)

        statement = select(Batch).where(*filters)

        column = {
            "name": Batch.name,
            "planned_qty": Batch.planned_qty,
            "day_plan_qty": Batch.day_plan_qty,
            "status": Batch.status,
            "created_at": Batch.created_at,
            "updated_at": Batch.updated_at,
            "completed_at": Batch.completed_at,
            "archived_at": Batch.archived_at,
        }[sort]

        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()

        statement = (
            statement.order_by(sorted_column, Batch.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count = await self._session.scalar(select(func.count()).select_from(Batch).where(*filters))

        result = await self._session.execute(statement)

        return list(result.scalars()), int(count or 0)

    async def exists_by_dev_eui_prefix(self, prefix: str) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(Batch.dev_eui_prefix == prefix)))
        )
