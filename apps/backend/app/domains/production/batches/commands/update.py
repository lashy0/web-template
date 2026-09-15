from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, batch_entity
from ..model import Batch
from ..queries import required_batch
from ..repository import BatchRepository
from ..rules import (
    BATCH_EDIT_WINDOW,
    ensure_batch_edit_allowed,
    ensure_management_allowed,
    ensure_not_archived,
)


class UpdateBatch:
    def __init__(
        self,
        repository: BatchRepository,
        audit: TransactionalAuditWriter,
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._edit_window = edit_window
        self._clock = clock

    async def execute(
        self, *, actor: CurrentPrincipal, batch_id: UUID, updates: Mapping[str, object]
    ) -> Batch:
        ensure_management_allowed(actor)
        batch = await required_batch(self._repository, batch_id, for_update=True)
        ensure_not_archived(batch)
        ensure_batch_edit_allowed(
            batch, actor=actor, now=self._clock(), edit_window=self._edit_window
        )
        if not updates:
            return batch
        old_values = {field: getattr(batch, field) for field in updates}
        batch = await self._repository.update(batch, updates=updates)
        changed = {
            field: getattr(batch, field)
            for field, old_value in old_values.items()
            if getattr(batch, field) != old_value
        }
        if changed:
            await self._audit.record(
                actor=audit_actor(actor),
                action="batch.updated",
                entity=batch_entity(batch),
                old_data={field: old_values[field] for field in changed},
                new_data=changed,
            )
        return batch
