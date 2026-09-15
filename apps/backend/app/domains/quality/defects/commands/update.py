from collections.abc import Mapping
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import DefectGroup, DefectType
from ..queries import required_group, required_type
from ..repository import DefectGroupRepository, DefectTypeRepository
from ._common import audit_actor, group_entity, type_entity


class UpdateDefectGroup:
    def __init__(self, repository: DefectGroupRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, group_id: UUID, updates: Mapping[str, object]
    ) -> DefectGroup:
        item = await required_group(self._repository, group_id)
        if not updates:
            return item
        old = {field: getattr(item, field) for field in updates}
        item = await self._repository.update(item, updates=updates)
        changed = {
            field: getattr(item, field)
            for field, value in old.items()
            if getattr(item, field) != value
        }
        if changed:
            await self._audit.record(
                actor=audit_actor(actor),
                action="defect_group.updated",
                entity=group_entity(item),
                old_data={field: old[field] for field in changed},
                new_data=changed,
            )
        return item


class UpdateDefectType:
    def __init__(self, repository: DefectTypeRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, defect_type_id: UUID, updates: Mapping[str, object]
    ) -> DefectType:
        item = await required_type(self._repository, defect_type_id)
        if not updates:
            return item
        old = {field: getattr(item, field) for field in updates}
        item = await self._repository.update(item, updates=updates)
        changed = {
            field: getattr(item, field)
            for field, value in old.items()
            if getattr(item, field) != value
        }
        if changed:
            await self._audit.record(
                actor=audit_actor(actor),
                action="defect_type.updated",
                entity=type_entity(item),
                old_data={field: old[field] for field in changed},
                new_data=changed,
            )
        return item
