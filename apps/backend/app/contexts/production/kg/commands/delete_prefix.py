from app.audit.writer import TransactionalAuditWriter
from app.modules.kg.exceptions import KgDevEuiPrefixInUseError
from app.modules.kg.permissions import KgPermission
from app.shared.security import CurrentPrincipal

from ..repository import KgRepository
from ._common import audit_actor, authorize, prefix_entity, required_prefix


class DeletePrefix:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(self, *, actor: CurrentPrincipal, prefix: str) -> None:
        authorize(actor, KgPermission.PREFIX_DELETE)
        await self._repository.lock_allocation(prefix)
        item = await required_prefix(self._repository, prefix)
        if await self._repository.count_batches_for_prefix(item.prefix):
            raise KgDevEuiPrefixInUseError
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg_prefix.deleted",
            entity=prefix_entity(item),
            old_data={"prefix": item.prefix, "short_code": item.short_code, "name": item.name},
        )
        await self._repository.delete_prefix(item)
