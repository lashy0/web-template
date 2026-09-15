from datetime import UTC, datetime
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import DefectGroup, DefectType
from ..queries import required_group, required_type
from ..repository import DefectGroupRepository, DefectTypeRepository
from ..rules import ensure_group_active, ensure_group_can_be_archived
from ._common import audit_actor, group_entity, type_entity


class SetDefectGroupArchived:
    def __init__(
        self,
        groups: DefectGroupRepository,
        types: DefectTypeRepository,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._groups = groups
        self._types = types
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, group_id: UUID, archived: bool
    ) -> DefectGroup:
        item = await required_group(self._groups, group_id)
        if archived:
            if item.archived_at is not None:
                return item
            ensure_group_can_be_archived(
                group=item,
                has_unarchived_types=await self._types.has_unarchived_group_usage(item.id),
            )
            item = await self._groups.set_archived(item, archived_at=datetime.now(UTC))
            action = "defect_group.archived"
        else:
            if item.archived_at is None:
                return item
            item = await self._groups.set_archived(item, archived_at=None)
            action = "defect_group.restored"
        await self._audit.record(actor=audit_actor(actor), action=action, entity=group_entity(item))
        return item


class SetDefectTypeArchived:
    def __init__(
        self,
        groups: DefectGroupRepository,
        types: DefectTypeRepository,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._groups = groups
        self._types = types
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, defect_type_id: UUID, archived: bool
    ) -> DefectType:
        item = await required_type(self._types, defect_type_id)
        if archived:
            if item.archived_at is not None:
                return item
            item = await self._types.set_archived(item, archived_at=datetime.now(UTC))
            action = "defect_type.archived"
        else:
            if item.archived_at is None:
                return item
            ensure_group_active(await required_group(self._groups, item.group_id))
            item = await self._types.set_archived(item, archived_at=None)
            action = "defect_type.restored"
        await self._audit.record(actor=audit_actor(actor), action=action, entity=type_entity(item))
        return item
