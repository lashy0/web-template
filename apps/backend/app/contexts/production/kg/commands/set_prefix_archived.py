from datetime import UTC, datetime

from app.audit.writer import TransactionalAuditWriter
from app.modules.kg.permissions import KgPermission
from app.shared.security import CurrentPrincipal

from ..model import KgDevEuiPrefix
from ..repository import KgRepository
from ._common import audit_actor, authorize, prefix_entity, required_prefix


class SetPrefixArchived:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, prefix: str, archived: bool
    ) -> KgDevEuiPrefix:
        authorize(actor, KgPermission.PREFIX_ARCHIVE)
        item = await required_prefix(self._repository, prefix)
        if archived == (item.archived_at is not None):
            return item
        item.archived_at = datetime.now(UTC) if archived else None
        item = await self._repository.save_prefix(item)
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg_prefix.archived" if archived else "kg_prefix.restored",
            entity=prefix_entity(item),
        )
        return item
