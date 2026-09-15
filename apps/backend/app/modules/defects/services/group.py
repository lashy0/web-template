"""Legacy caller-UoW compatibility delegate for the migrated defect context."""

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.contexts.quality.defects.commands import (
    CreateDefectGroup,
    DeleteDefectGroup,
    SetDefectGroupArchived,
    UpdateDefectGroup,
)
from app.contexts.quality.defects.model import DefectGroup
from app.contexts.quality.defects.queries import DefectQueries
from app.contexts.quality.defects.repository import DefectGroupRepository, DefectTypeRepository
from app.shared.security import CurrentPrincipal


class DefectGroupService:
    """Temporary legacy import adapter; contains no defect policy."""

    def __init__(self, session: AsyncSession) -> None:
        self._groups = DefectGroupRepository(session)
        self._types = DefectTypeRepository(session)
        self._audit = TransactionalAuditWriter.from_session(session)

    async def get_group(self, group_id: UUID) -> DefectGroup | None:
        return await DefectQueries(self._groups, self._types).get_group(group_id)

    async def get_group_by_code(self, code: str, *, for_update: bool = False) -> DefectGroup | None:
        return await DefectQueries(self._groups, self._types).get_group_by_code(
            code, for_update=for_update
        )

    async def list_groups(self, **kwargs: object) -> tuple[list[tuple[DefectGroup, int, int]], int]:
        return await DefectQueries(self._groups, self._types).list_groups(**kwargs)

    async def create_group(
        self, *, actor: CurrentPrincipal, code: str, name: str, description: str | None
    ) -> DefectGroup:
        return await CreateDefectGroup(self._groups, self._audit).execute(
            actor=actor, code=code, name=name, description=description
        )

    async def update_group(
        self, *, actor: CurrentPrincipal, group_id: UUID, updates: Mapping[str, object]
    ) -> DefectGroup:
        return await UpdateDefectGroup(self._groups, self._audit).execute(
            actor=actor, group_id=group_id, updates=updates
        )

    async def set_group_archived(
        self, *, actor: CurrentPrincipal, group_id: UUID, archived: bool
    ) -> DefectGroup:
        return await SetDefectGroupArchived(self._groups, self._types, self._audit).execute(
            actor=actor, group_id=group_id, archived=archived
        )

    async def delete_group(self, *, actor: CurrentPrincipal, group_id: UUID) -> None:
        await DeleteDefectGroup(self._groups, self._types, self._audit).execute(
            actor=actor, group_id=group_id
        )
