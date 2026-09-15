from datetime import UTC, datetime
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import KgVersion
from ..permissions import KgPermission
from ..repository import KgRepository
from ._common import audit_actor, authorize, required_version, version_entity


class SetVersionArchived:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, version_id: UUID, archived: bool
    ) -> KgVersion:
        authorize(actor, KgPermission.VERSION_ARCHIVE)
        item = await required_version(self._repository, version_id)
        if archived == (item.archived_at is not None):
            return item
        old_archived_at = item.archived_at
        item.archived_at = datetime.now(UTC) if archived else None
        item = await self._repository.save_version(item)
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg_version.archived" if archived else "kg_version.restored",
            entity=version_entity(item),
            old_data={"archived_at": old_archived_at.isoformat() if old_archived_at else None},
            new_data={"archived_at": item.archived_at.isoformat() if item.archived_at else None},
        )
        return item
