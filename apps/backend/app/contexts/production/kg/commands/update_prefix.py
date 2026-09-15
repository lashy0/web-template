from collections.abc import Mapping

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import KgDevEuiPrefix
from ..permissions import KgPermission
from ..repository import KgRepository
from ._common import audit_actor, authorize, prefix_entity, required_prefix


class UpdatePrefix:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, prefix: str, updates: Mapping[str, object]
    ) -> KgDevEuiPrefix:
        authorize(actor, KgPermission.PREFIX_UPDATE)
        item = await required_prefix(self._repository, prefix)
        if not updates:
            return item
        old = {field: getattr(item, field) for field in updates}
        for field, value in updates.items():
            setattr(item, field, value)
        item = await self._repository.save_prefix(item)
        changed = {
            field: getattr(item, field) for field in updates if getattr(item, field) != old[field]
        }
        if changed:
            await self._audit.record(
                actor=audit_actor(actor),
                action="kg_prefix.updated",
                entity=prefix_entity(item),
                old_data={field: old[field] for field in changed},
                new_data=changed,
            )
        return item
