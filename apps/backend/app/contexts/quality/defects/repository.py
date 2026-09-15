from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .model import DefectGroup, DefectType


class DefectGroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, code: str, name: str, description: str | None) -> DefectGroup:
        item = DefectGroup(code=code, name=name, description=description)
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def get(self, group_id: UUID, *, for_update: bool = False) -> DefectGroup | None:
        return await self._session.get(
            DefectGroup, group_id, with_for_update=for_update, populate_existing=for_update
        )

    async def get_by_code(self, code: str, *, for_update: bool = False) -> DefectGroup | None:
        statement = select(DefectGroup).where(DefectGroup.code == code)
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def update(self, item: DefectGroup, *, updates: Mapping[str, object]) -> DefectGroup:
        for field, value in updates.items():
            setattr(item, field, value)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def set_archived(self, item: DefectGroup, *, archived_at: datetime | None) -> DefectGroup:
        item.archived_at = archived_at
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def delete(self, item: DefectGroup) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def search(
        self, *, q: str | None, archived: bool, page: int, page_size: int, sort: str, order: str
    ) -> tuple[list[tuple[DefectGroup, int, int]], int]:
        filters: list[ColumnElement[bool]] = [
            DefectGroup.archived_at.is_not(None) if archived else DefectGroup.archived_at.is_(None)
        ]
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    DefectGroup.code.ilike(pattern),
                    DefectGroup.name.ilike(pattern),
                    DefectGroup.description.ilike(pattern),
                )
            )
        active_types = func.count(DefectType.id).filter(DefectType.archived_at.is_(None))
        all_types = func.count(DefectType.id)
        column = {
            name: getattr(DefectGroup, name)
            for name in ("code", "name", "created_at", "updated_at", "archived_at")
        }[sort]
        ordered = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        result = await self._session.execute(
            select(DefectGroup, active_types, all_types)
            .outerjoin(DefectType, DefectType.group_id == DefectGroup.id)
            .where(*filters)
            .group_by(DefectGroup.id)
            .order_by(ordered, DefectGroup.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(DefectGroup).where(*filters)
        )
        return [(item, int(active), int(total)) for item, active, total in result.tuples()], int(
            count or 0
        )


class DefectTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        group_id: UUID,
        code: str,
        name: str,
        description: str,
        possible_cause: str | None,
        engineer_action: str | None,
    ) -> DefectType:
        item = DefectType(
            group_id=group_id,
            code=code,
            name=name,
            description=description,
            possible_cause=possible_cause,
            engineer_action=engineer_action,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def get(self, item_id: UUID, *, for_update: bool = False) -> DefectType | None:
        return await self._session.get(
            DefectType, item_id, with_for_update=for_update, populate_existing=for_update
        )

    async def get_by_code(self, code: str) -> DefectType | None:
        return (
            await self._session.execute(select(DefectType).where(DefectType.code == code))
        ).scalar_one_or_none()

    async def update(self, item: DefectType, *, updates: Mapping[str, object]) -> DefectType:
        for field, value in updates.items():
            setattr(item, field, value)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def set_archived(self, item: DefectType, *, archived_at: datetime | None) -> DefectType:
        item.archived_at = archived_at
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def delete(self, item: DefectType) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def search(
        self,
        *,
        q: str | None,
        group_id: UUID | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[DefectType], int]:
        filters: list[ColumnElement[bool]] = [
            DefectType.archived_at.is_not(None) if archived else DefectType.archived_at.is_(None)
        ]
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    DefectType.code.ilike(pattern),
                    DefectType.name.ilike(pattern),
                    DefectType.description.ilike(pattern),
                )
            )
        if group_id is not None:
            filters.append(DefectType.group_id == group_id)
        column = {
            name: getattr(DefectType, name)
            for name in ("code", "name", "created_at", "updated_at", "archived_at")
        }[sort]
        ordered = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        result = await self._session.execute(
            select(DefectType)
            .where(*filters)
            .order_by(ordered, DefectType.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(DefectType).where(*filters)
        )
        return list(result.scalars()), int(count or 0)

    async def has_group_usage(self, group_id: UUID) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(DefectType.group_id == group_id)))
        )

    async def has_unarchived_group_usage(self, group_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        DefectType.group_id == group_id, DefectType.archived_at.is_(None)
                    )
                )
            )
        )
