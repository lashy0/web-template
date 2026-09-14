from typing import cast
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

# KgUnit remains legacy; Batch itself is now owned by the batches subdomain.
from app.contexts.production.batches.model import Batch
from app.modules.kg.models import KgUnit

from .model import KgDevEuiPrefix, KgVersion


class KgRepository:
    """Persistence and PostgreSQL concurrency primitives for the migrated KG slice."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_prefix(self, prefix: str, *, for_update: bool = False) -> KgDevEuiPrefix | None:
        return await self._session.get(
            KgDevEuiPrefix,
            prefix,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_prefix_by_short_code(self, short_code: str) -> KgDevEuiPrefix | None:
        return (
            await self._session.scalars(
                select(KgDevEuiPrefix).where(KgDevEuiPrefix.short_code == short_code).limit(1)
            )
        ).first()

    async def list_prefixes(
        self, *, q: str | None, archived: bool, page: int, page_size: int, sort: str, order: str
    ) -> tuple[list[tuple[KgDevEuiPrefix, int]], int]:
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
        counts = (
            select(Batch.dev_eui_prefix.label("prefix"), func.count(Batch.id).label("batch_count"))
            .group_by(Batch.dev_eui_prefix)
            .subquery()
        )
        result = await self._session.execute(
            select(KgDevEuiPrefix, func.coalesce(counts.c.batch_count, 0).label("batch_count"))
            .outerjoin(counts, counts.c.prefix == KgDevEuiPrefix.prefix)
            .where(*filters)
            .order_by(sorted_column, KgDevEuiPrefix.prefix.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(KgDevEuiPrefix).where(*filters)
        )
        return [(item, int(batch_count)) for item, batch_count in result.tuples()], int(count or 0)

    async def count_batches_for_prefix(self, prefix: str) -> int:
        count = await self._session.scalar(
            select(func.count(Batch.id)).where(Batch.dev_eui_prefix == prefix)
        )
        return int(count or 0)

    async def save_prefix(self, item: KgDevEuiPrefix) -> KgDevEuiPrefix:
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def delete_prefix(self, item: KgDevEuiPrefix) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def get_version(self, version_id: UUID, *, for_update: bool = False) -> KgVersion | None:
        return await self._session.get(
            KgVersion, version_id, with_for_update=for_update, populate_existing=for_update
        )

    async def get_version_by_code(self, code: str) -> KgVersion | None:
        return (
            await self._session.scalars(select(KgVersion).where(KgVersion.code == code).limit(1))
        ).first()

    async def list_versions(
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
        counts = (
            select(
                Batch.kg_version_id.label("version_id"), func.count(Batch.id).label("batch_count")
            )
            .where(Batch.kg_version_id.is_not(None))
            .group_by(Batch.kg_version_id)
            .subquery()
        )
        result = await self._session.execute(
            select(KgVersion, func.coalesce(counts.c.batch_count, 0).label("batch_count"))
            .outerjoin(counts, counts.c.version_id == KgVersion.id)
            .where(*filters)
            .order_by(sorted_column, KgVersion.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(KgVersion).where(*filters)
        )
        return [(item, int(batch_count)) for item, batch_count in result.tuples()], int(count or 0)

    async def count_batches_for_version(self, version_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count(Batch.id)).where(Batch.kg_version_id == version_id)
        )
        return int(count or 0)

    async def save_version(self, item: KgVersion) -> KgVersion:
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def delete_version(self, item: KgVersion) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def lock_allocation(self, prefix: str) -> None:
        await self._session.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"kg-dev-eui:{prefix}")))
        )

    async def get_max_dev_eui_for_prefix(self, prefix: str) -> str | None:
        return cast(
            str | None,
            await self._session.scalar(
                select(func.max(KgUnit.dev_eui)).where(KgUnit.dev_eui.like(f"{prefix}%"))
            ),
        )
