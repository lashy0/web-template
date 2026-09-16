from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .model import Check


class CheckRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, test_name: str, test_label: str, defect_group_id: UUID, last_seen_at: datetime
    ) -> Check:
        item = Check(
            test_name=test_name,
            test_label=test_label,
            defect_group_id=defect_group_id,
            last_seen_at=last_seen_at,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def get(self, test_id: UUID) -> Check | None:
        return await self._session.get(Check, test_id)

    async def get_by_id(self, test_id: UUID) -> Check | None:
        """Compatibility spelling used by legacy verification tests."""
        return await self.get(test_id)

    async def get_by_test_name(self, test_name: str) -> Check | None:
        return (
            await self._session.execute(select(Check).where(Check.test_name == test_name))
        ).scalar_one_or_none()

    async def update_observation(
        self, item: Check, *, test_label: str, defect_group_id: UUID, last_seen_at: datetime
    ) -> Check:
        item.test_label = test_label
        item.defect_group_id = defect_group_id
        item.last_seen_at = last_seen_at
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def search(
        self,
        *,
        q: str | None,
        defect_group_id: UUID | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[Check], int]:
        filters: list[ColumnElement[bool]] = []
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(or_(Check.test_name.ilike(pattern), Check.test_label.ilike(pattern)))
        if defect_group_id is not None:
            filters.append(Check.defect_group_id == defect_group_id)
        column = {
            name: getattr(Check, name)
            for name in ("test_name", "test_label", "last_seen_at", "created_at", "updated_at")
        }[sort]
        ordered = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        result = await self._session.execute(
            select(Check)
            .where(*filters)
            .order_by(ordered, Check.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(Check).where(*filters)
        )
        return list(result.scalars()), int(count or 0)
