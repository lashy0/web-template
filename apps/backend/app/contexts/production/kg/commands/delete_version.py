from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..exceptions import KgVersionInUseError
from ..permissions import KgPermission
from ..repository import KgRepository
from ._common import audit_actor, authorize, required_version, version_entity


class DeleteVersion:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(self, *, actor: CurrentPrincipal, version_id: UUID) -> None:
        authorize(actor, KgPermission.VERSION_DELETE)
        item = await required_version(self._repository, version_id)
        if await self._repository.count_batches_for_version(item.id):
            raise KgVersionInUseError
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg_version.deleted",
            entity=version_entity(item),
            old_data={"code": item.code, "name": item.name, "description": item.description},
        )
        await self._repository.delete_version(item)
