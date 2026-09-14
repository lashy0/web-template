from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.preparation.repository import PreparationRepository
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, batch_entity
from ..model import Batch
from ..queries import required_batch
from ..repository import BatchRepository
from ..rules import ensure_in_production, ensure_management_allowed


class CompleteBatch:
    def __init__(
        self,
        repository: BatchRepository,
        preparation: PreparationRepository,
        audit: TransactionalAuditWriter,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._preparation = preparation
        self._audit = audit
        self._clock = clock

    async def execute(self, *, actor: CurrentPrincipal, batch_id: UUID) -> Batch:
        ensure_management_allowed(actor)
        batch = await required_batch(self._repository, batch_id, for_update=True)
        job = await self._preparation.get(batch.id, for_update=True)
        ensure_in_production(batch, preparation_status=job.status if job is not None else None)
        old_status = batch.status
        completed_at = self._clock()
        batch = await self._repository.complete(batch, completed_at=completed_at)
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch.completed",
            entity=batch_entity(batch),
            old_data={"status": old_status.value, "completed_at": None},
            new_data={"status": batch.status.value, "completed_at": completed_at.isoformat()},
        )
        return batch
