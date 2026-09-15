from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, batch_entity
from ..model import Batch
from ..queries import required_batch
from ..repository import BatchRepository
from ..rules import ensure_management_allowed


class SetBatchArchived:
    def __init__(
        self,
        repository: BatchRepository,
        audit: TransactionalAuditWriter,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._clock = clock

    async def execute(self, *, actor: CurrentPrincipal, batch_id: UUID, archived: bool) -> Batch:
        ensure_management_allowed(actor)
        batch = await required_batch(self._repository, batch_id, for_update=True)
        if archived:
            if batch.archived_at is not None:
                return batch
            archived_at = self._clock()
            batch = await self._repository.set_archived(batch, archived_at=archived_at)
            action = "batch.archived"
            old_data: dict[str, str | None] = {"archived_at": None}
            new_data: dict[str, str | None] = {"archived_at": archived_at.isoformat()}
        else:
            if batch.archived_at is None:
                return batch
            old_archived_at = batch.archived_at
            batch = await self._repository.set_archived(batch, archived_at=None)
            action = "batch.restored"
            old_data = {"archived_at": old_archived_at.isoformat()}
            new_data = {"archived_at": None}
        await self._audit.record(
            actor=audit_actor(actor),
            action=action,
            entity=batch_entity(batch),
            old_data=old_data,
            new_data=new_data,
        )
        return batch
