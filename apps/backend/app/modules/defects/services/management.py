from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal

from ..models import DefectGroup, DefectType
from .group import DefectGroupService as DefectGroupService
from .type import DefectTypeService


class DefectManagementService:
    """Public compatibility gateway for the domain services."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_group(self, group_id: UUID) -> DefectGroup | None:
        async with self._session_factory() as session:
            return await DefectGroupService(session).get_group(group_id)

    async def get_group_by_code(self, code: str) -> DefectGroup | None:
        async with self._session_factory() as session:
            return await DefectGroupService(session).get_group_by_code(code)

    async def list_groups(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[DefectGroup, int, int]], int]:
        async with self._session_factory() as session:
            return await DefectGroupService(session).list_groups(
                q=q,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def create_group(
        self,
        *,
        actor: CurrentPrincipal,
        code: str,
        name: str,
        description: str | None,
    ) -> DefectGroup:
        async with self._session_factory() as session, session.begin():
            return await DefectGroupService(session).create_group(
                actor=actor,
                code=code,
                name=name,
                description=description,
            )

    async def update_group(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
        updates: Mapping[str, object],
    ) -> DefectGroup:
        async with self._session_factory() as session, session.begin():
            return await DefectGroupService(session).update_group(
                actor=actor,
                group_id=group_id,
                updates=updates,
            )

    async def set_group_archived(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
        archived: bool,
    ) -> DefectGroup:
        async with self._session_factory() as session, session.begin():
            return await DefectGroupService(session).set_group_archived(
                actor=actor,
                group_id=group_id,
                archived=archived,
            )

    async def delete_group(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            return await DefectGroupService(session).delete_group(actor=actor, group_id=group_id)

    async def get_type(self, defect_type_id: UUID) -> DefectType | None:
        async with self._session_factory() as session:
            return await DefectTypeService(session).get_type(defect_type_id)

    async def get_type_by_code(self, code: str) -> DefectType | None:
        async with self._session_factory() as session:
            return await DefectTypeService(session).get_type_by_code(code)

    async def list_types(
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
        async with self._session_factory() as session:
            return await DefectTypeService(session).list_types(
                q=q,
                group_id=group_id,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def create_type(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
        code: str,
        name: str,
        description: str,
        possible_cause: str | None,
        engineer_action: str | None,
    ) -> DefectType:
        async with self._session_factory() as session, session.begin():
            return await DefectTypeService(session).create_type(
                actor=actor,
                group_id=group_id,
                code=code,
                name=name,
                description=description,
                possible_cause=possible_cause,
                engineer_action=engineer_action,
            )

    async def update_type(
        self,
        *,
        actor: CurrentPrincipal,
        defect_type_id: UUID,
        updates: Mapping[str, object],
    ) -> DefectType:
        async with self._session_factory() as session, session.begin():
            return await DefectTypeService(session).update_type(
                actor=actor, defect_type_id=defect_type_id, updates=updates
            )

    async def set_type_archived(
        self,
        *,
        actor: CurrentPrincipal,
        defect_type_id: UUID,
        archived: bool,
    ) -> DefectType:
        async with self._session_factory() as session, session.begin():
            return await DefectTypeService(session).set_type_archived(
                actor=actor, defect_type_id=defect_type_id, archived=archived
            )

    async def delete_type(
        self,
        *,
        actor: CurrentPrincipal,
        defect_type_id: UUID,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            return await DefectTypeService(session).delete_type(
                actor=actor, defect_type_id=defect_type_id
            )
