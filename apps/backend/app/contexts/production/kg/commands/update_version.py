from collections.abc import Mapping
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import KgVersion
from ..permissions import KgPermission
from ..repository import KgRepository
from ._common import audit_actor, authorize, required_version, version_entity


class UpdateVersion:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, version_id: UUID, updates: Mapping[str, object]
    ) -> KgVersion:
        authorize(actor, KgPermission.VERSION_UPDATE)
        item = await required_version(self._repository, version_id)
        if not updates:
            return item
        old = {field: getattr(item, field) for field in updates}
        for field, value in updates.items():
            setattr(item, field, value)
        item = await self._repository.save_version(item)
        changed = {
            field: getattr(item, field) for field in updates if getattr(item, field) != old[field]
        }
        if changed:
            await self._audit.record(
                actor=audit_actor(actor),
                action="kg_version.updated",
                entity=version_entity(item),
                old_data={field: old[field] for field in changed},
                new_data=changed,
            )
        return item
