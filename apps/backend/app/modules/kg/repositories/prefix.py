from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ..models import KgDevEuiPrefix


class KgDevEuiPrefixRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        prefix: str,
        *,
        for_update: bool = False,
    ) -> KgDevEuiPrefix | None:
        return await self._session.get(
            KgDevEuiPrefix,
            prefix,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_by_short_code(self, short_code: str) -> KgDevEuiPrefix | None:
        result = await self._session.scalars(
            select(KgDevEuiPrefix).where(KgDevEuiPrefix.short_code == short_code).limit(1)
        )

        return result.first()

    async def search(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[KgDevEuiPrefix], int]:
        filters: list[ColumnElement[bool]] = [
            KgDevEuiPrefix.archived_at.is_not(None)
            if archived
            else KgDevEuiPrefix.archived_at.is_(None)
        ]

        if q:
            pattern = f"%{q}%"
            filters.append(
                or_(
                    KgDevEuiPrefix.prefix.ilike(pattern),
                    KgDevEuiPrefix.short_code.ilike(pattern),
                    KgDevEuiPrefix.name.ilike(pattern),
                )
            )

        column = {
            "prefix": KgDevEuiPrefix.prefix,
            "name": KgDevEuiPrefix.name,
            "short_code": KgDevEuiPrefix.short_code,
            "created_at": KgDevEuiPrefix.created_at,
            "archived_at": KgDevEuiPrefix.archived_at,
        }[sort]

        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        result = await self._session.execute(
            select(KgDevEuiPrefix)
            .where(*filters)
            .order_by(sorted_column, KgDevEuiPrefix.prefix.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(KgDevEuiPrefix).where(*filters)
        )

        return list(result.scalars()), int(count or 0)

    async def create(
        self,
        *,
        prefix: str,
        short_code: str,
        name: str | None,
    ) -> KgDevEuiPrefix:
        item = KgDevEuiPrefix(
            prefix=prefix,
            short_code=short_code,
            name=name,
        )

        self._session.add(item)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def update_details(
        self,
        item: KgDevEuiPrefix,
        *,
        updates: Mapping[str, object],
    ) -> KgDevEuiPrefix:
        for field, value in updates.items():
            setattr(item, field, value)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def update_archived(
        self,
        item: KgDevEuiPrefix,
        *,
        archived_at: datetime | None,
    ) -> KgDevEuiPrefix:
        item.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def delete(self, item: KgDevEuiPrefix) -> None:
        await self._session.delete(item)
        await self._session.flush()
