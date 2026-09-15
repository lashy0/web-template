from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..exceptions import DefectGroupCannotBeDeletedError, DefectTypeCannotBeDeletedError
from ..queries import required_group, required_type
from ..repository import DefectGroupRepository, DefectTypeRepository
from ..rules import group_snapshot, type_snapshot
from ._common import audit_actor, group_entity, type_entity


class DeleteDefectGroup:
    def __init__(
        self,
        groups: DefectGroupRepository,
        types: DefectTypeRepository,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._groups = groups
        self._types = types
        self._audit = audit

    async def execute(self, *, actor: CurrentPrincipal, group_id: UUID) -> None:
        item = await required_group(self._groups, group_id)
        if await self._types.has_group_usage(item.id):
            raise DefectGroupCannotBeDeletedError
        await self._audit.record(
            actor=audit_actor(actor),
            action="defect_group.deleted",
            entity=group_entity(item),
            old_data=group_snapshot(item),
        )
        try:
            await self._groups.delete(item)
        except IntegrityError as exc:
            raise DefectGroupCannotBeDeletedError from exc


class DeleteDefectType:
    def __init__(self, repository: DefectTypeRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(self, *, actor: CurrentPrincipal, defect_type_id: UUID) -> None:
        item = await required_type(self._repository, defect_type_id)
        await self._audit.record(
            actor=audit_actor(actor),
            action="defect_type.deleted",
            entity=type_entity(item),
            old_data=type_snapshot(item),
        )
        try:
            await self._repository.delete(item)
        except IntegrityError as exc:
            raise DefectTypeCannotBeDeletedError from exc
