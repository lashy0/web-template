"""Legacy caller-UoW compatibility delegate for the migrated defect context."""

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.contexts.quality.defects.commands import (
    CreateDefectType,
    DeleteDefectType,
    SetDefectTypeArchived,
    UpdateDefectType,
)
from app.contexts.quality.defects.model import DefectType
from app.contexts.quality.defects.queries import DefectQueries
from app.contexts.quality.defects.repository import DefectGroupRepository, DefectTypeRepository
from app.shared.security import CurrentPrincipal


class DefectTypeService:
    """Temporary legacy import adapter; contains no defect policy."""

    def __init__(self, session: AsyncSession) -> None:
        self._groups = DefectGroupRepository(session)
        self._types = DefectTypeRepository(session)
        self._audit = TransactionalAuditWriter.from_session(session)

    async def get_type(self, item_id: UUID) -> DefectType | None:
        return await DefectQueries(self._groups, self._types).get_type(item_id)

    async def get_type_by_code(self, code: str) -> DefectType | None:
        return await DefectQueries(self._groups, self._types).get_type_by_code(code)

    async def list_types(self, **kwargs: object) -> tuple[list[DefectType], int]:
        return await DefectQueries(self._groups, self._types).list_types(**kwargs)

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
        return await CreateDefectType(self._groups, self._types, self._audit).execute(
            actor=actor,
            group_id=group_id,
            code=code,
            name=name,
            description=description,
            possible_cause=possible_cause,
            engineer_action=engineer_action,
        )

    async def update_type(
        self, *, actor: CurrentPrincipal, defect_type_id: UUID, updates: Mapping[str, object]
    ) -> DefectType:
        return await UpdateDefectType(self._types, self._audit).execute(
            actor=actor, defect_type_id=defect_type_id, updates=updates
        )

    async def set_type_archived(
        self, *, actor: CurrentPrincipal, defect_type_id: UUID, archived: bool
    ) -> DefectType:
        return await SetDefectTypeArchived(self._groups, self._types, self._audit).execute(
            actor=actor, defect_type_id=defect_type_id, archived=archived
        )

    async def delete_type(self, *, actor: CurrentPrincipal, defect_type_id: UUID) -> None:
        await DeleteDefectType(self._types, self._audit).execute(
            actor=actor, defect_type_id=defect_type_id
        )
