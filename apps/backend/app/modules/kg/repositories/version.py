from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.batch.models import Batch

from ..models import KgVersion


class KgVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        version_id: UUID,
        *,
        for_update: bool = False,
    ) -> KgVersion | None:
        return await self._session.get(
            KgVersion,
            version_id,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_by_code(self, code: str) -> KgVersion | None:
        result = await self._session.scalars(
            select(KgVersion).where(KgVersion.code == code).limit(1)
        )

        return result.first()

    async def count_batches(self, version_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count(Batch.id)).where(Batch.kg_version_id == version_id)
        )

        return int(count or 0)

    async def search(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[KgVersion, int]], int]:
        filters: list[ColumnElement[bool]] = [
            KgVersion.archived_at.is_not(None) if archived else KgVersion.archived_at.is_(None)
        ]

        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    KgVersion.code.ilike(pattern),
                    KgVersion.name.ilike(pattern),
                    KgVersion.description.ilike(pattern),
                )
            )

        column = {
            "code": KgVersion.code,
            "name": KgVersion.name,
            "description": KgVersion.description,
            "created_at": KgVersion.created_at,
            "updated_at": KgVersion.updated_at,
            "archived_at": KgVersion.archived_at,
        }[sort_by]

        sorted_column = (
            column.desc().nulls_last() if sort_order == "desc" else column.asc().nulls_last()
        )

        batch_counts = (
            select(
                Batch.kg_version_id.label("version_id"),
                func.count(Batch.id).label("batch_count"),
            )
            .where(Batch.kg_version_id.is_not(None))
            .group_by(Batch.kg_version_id)
            .subquery()
        )

        result = await self._session.execute(
            select(
                KgVersion,
                func.coalesce(batch_counts.c.batch_count, 0).label("batch_count"),
            )
            .outerjoin(batch_counts, batch_counts.c.version_id == KgVersion.id)
            .where(*filters)
            .order_by(sorted_column, KgVersion.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count = await self._session.scalar(
            select(func.count()).select_from(KgVersion).where(*filters)
        )

        return [(item, int(batch_count)) for item, batch_count in result.tuples()], int(count or 0)

    async def create(
        self,
        *,
        code: str,
        name: str,
        description: str | None,
    ) -> KgVersion:
        item = KgVersion(
            code=code,
            name=name,
            description=description,
        )
        self._session.add(item)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def update_details(
        self,
        item: KgVersion,
        *,
        updates: Mapping[str, object],
    ) -> KgVersion:
        for field, value in updates.items():
            setattr(item, field, value)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def update_archived(
        self,
        item: KgVersion,
        *,
        archived_at: datetime | None,
    ) -> KgVersion:
        item.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def delete(self, item: KgVersion) -> None:
        await self._session.delete(item)
        await self._session.flush()
