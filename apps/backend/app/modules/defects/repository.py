from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.defects.models import DefectGroup, DefectType


class DefectGroupRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        code: str,
        name: str,
        description: str | None,
    ) -> DefectGroup:
        group = DefectGroup(
            code=code,
            name=name,
            description=description,
        )

        self._session.add(group)

        await self._session.flush()
        await self._session.refresh(group)

        return group

    async def get_by_id(self, group_id: UUID) -> DefectGroup | None:
        return await self._session.get(DefectGroup, group_id)

    async def get_by_code(self, code: str) -> DefectGroup | None:
        statement = select(DefectGroup).where(DefectGroup.code == code)

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def update_details(
        self,
        group: DefectGroup,
        *,
        updates: Mapping[str, object],
    ) -> DefectGroup:
        for field, value in updates.items():
            setattr(group, field, value)

        await self._session.flush()
        await self._session.refresh(group)

        return group

    async def update_archived(
        self,
        group: DefectGroup,
        *,
        archived_at: datetime | None,
    ) -> DefectGroup:
        group.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(group)

        return group

    async def delete(self, group: DefectGroup) -> None:
        await self._session.delete(group)
        await self._session.flush()

    async def search(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[DefectGroup, int, int]], int]:
        filters: list[ColumnElement[bool]] = [
            (
                DefectGroup.archived_at.is_not(None)
                if archived
                else DefectGroup.archived_at.is_(None)
            )
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

        active_types_count = func.count(DefectType.id).filter(DefectType.archived_at.is_(None))
        types_count = func.count(DefectType.id)
        statement = (
            select(DefectGroup, active_types_count, types_count)
            .outerjoin(DefectType, DefectType.group_id == DefectGroup.id)
            .where(*filters)
            .group_by(DefectGroup.id)
        )

        column = {
            "code": DefectGroup.code,
            "name": DefectGroup.name,
            "created_at": DefectGroup.created_at,
            "updated_at": DefectGroup.updated_at,
            "archived_at": DefectGroup.archived_at,
        }[sort]

        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()

        statement = (
            statement.order_by(
                sorted_column,
                DefectGroup.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count = await self._session.scalar(
            select(func.count()).select_from(DefectGroup).where(*filters)
        )

        result = await self._session.execute(statement)

        return [
            (group, int(active_types_count), int(types_count))
            for group, active_types_count, types_count in result.tuples()
        ], int(count or 0)


class DefectTypeRepository:
    def __init__(self, session: AsyncSession):
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
        defect_type = DefectType(
            group_id=group_id,
            code=code,
            name=name,
            description=description,
            possible_cause=possible_cause,
            engineer_action=engineer_action,
        )

        self._session.add(defect_type)

        await self._session.flush()
        await self._session.refresh(defect_type)

        return defect_type

    async def get_by_id(self, defect_type_id: UUID) -> DefectType | None:
        return await self._session.get(DefectType, defect_type_id)

    async def get_by_code(self, code: str) -> DefectType | None:
        statement = select(DefectType).where(DefectType.code == code)

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def update_details(
        self,
        defect_type: DefectType,
        *,
        updates: Mapping[str, object],
    ) -> DefectType:
        for field, value in updates.items():
            setattr(defect_type, field, value)

        await self._session.flush()
        await self._session.refresh(defect_type)

        return defect_type

    async def update_archived(
        self,
        defect_type: DefectType,
        *,
        archived_at: datetime | None,
    ) -> DefectType:
        defect_type.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(defect_type)

        return defect_type

    async def delete(
        self,
        defect_type: DefectType,
    ) -> None:
        await self._session.delete(defect_type)
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
            (DefectType.archived_at.is_not(None) if archived else DefectType.archived_at.is_(None))
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

        statement = select(DefectType).where(*filters)

        column = {
            "code": DefectType.code,
            "name": DefectType.name,
            "created_at": DefectType.created_at,
            "updated_at": DefectType.updated_at,
            "archived_at": DefectType.archived_at,
        }[sort]

        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()

        statement = (
            statement.order_by(
                sorted_column,
                DefectType.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count = await self._session.scalar(
            select(func.count()).select_from(DefectType).where(*filters)
        )

        result = await self._session.execute(statement)

        return list(result.scalars()), int(count or 0)

    async def exists_by_group(self, group_id: UUID) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(DefectType.group_id == group_id)))
        )

    async def exists_unarchived_by_group(self, group_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        DefectType.group_id == group_id,
                        DefectType.archived_at.is_(None),
                    )
                )
            )
        )
