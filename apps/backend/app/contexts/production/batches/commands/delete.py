"""Multi-transaction batch deletion synchronized with preparation chunks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.kg.repository import KgRepository
from app.contexts.production.preparation.commands.request_cancellation import request_cancellation
from app.contexts.production.preparation.model import BatchKeyGenerationStatus
from app.contexts.production.preparation.notifier import ProgressNotifier
from app.contexts.production.preparation.repository import PreparationRepository
from app.contexts.production.receipts.repository import ReceiptRepository
from app.contexts.production.shipments.repository import ShipmentRepository
from app.modules.batch.exceptions import BatchCannotBeDeletedError
from app.shared.security import CurrentPrincipal
from app.shared.uow import transaction

from ..audit import audit_actor, batch_entity
from ..contracts import VerificationHistoryPort
from ..model import Batch, BatchStatus
from ..queries import required_batch
from ..repository import BatchRepository
from ..rules import (
    BATCH_EDIT_WINDOW,
    ensure_batch_edit_allowed,
    ensure_management_allowed,
    ensure_not_archived,
)

VerificationHistoryFactory = Callable[[AsyncSession], VerificationHistoryPort]


@dataclass(frozen=True, slots=True)
class _CancellationRequested:
    progress: int


class DeleteBatch:
    """Delete an eligible batch without owning a long-running transaction."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        verification_history: VerificationHistoryFactory,
        notifier: ProgressNotifier,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._verification_history = verification_history
        self._notifier = notifier
        self._edit_window = edit_window
        self._clock = clock

    async def execute(self, *, actor: CurrentPrincipal, batch_id: UUID) -> None:
        ensure_management_allowed(actor)
        cancellation = await self._request_cancellation_or_delete(actor=actor, batch_id=batch_id)
        if cancellation is None:
            return

        # This happens only after phase 1 committed. Redis is best-effort and
        # cannot undo the authoritative database transition.
        try:
            self._notifier.publish(
                batch_id, BatchKeyGenerationStatus.CANCELLING, cancellation.progress
            )
        except Exception:
            logger.bind(
                event="batch.preparation_notification_failed", batch_id=str(batch_id)
            ).exception("Could not publish committed batch preparation cancellation")

        await self._cleanup_cancelled_preparation(actor=actor, batch_id=batch_id)

    async def _request_cancellation_or_delete(
        self, *, actor: CurrentPrincipal, batch_id: UUID
    ) -> _CancellationRequested | None:
        async with transaction(self._session_factory) as session:
            batches = BatchRepository(session)
            batch = await required_batch(batches, batch_id, for_update=True)
            self._ensure_deletable_basics(batch, actor=actor)

            if await ReceiptRepository(session).has_receipts(batch.id):
                raise BatchCannotBeDeletedError
            if await ShipmentRepository(session).has_shipments(batch.id):
                raise BatchCannotBeDeletedError

            kg_units = KgRepository(session)
            if await kg_units.has_scrapped_by_batch(batch.id):
                raise BatchCannotBeDeletedError
            if await self._verification_history(session).has_history_for_batch(batch.id):
                raise BatchCannotBeDeletedError

            preparation = PreparationRepository(session)
            job = await preparation.get(batch.id, for_update=True)
            if job is not None and job.status is not BatchKeyGenerationStatus.READY:
                await request_cancellation(preparation, job)
                return _CancellationRequested(progress=job.progress)

            await self._delete_in_current_transaction(
                batch=batch,
                actor=actor,
                kg_units=kg_units,
                batches=batches,
                audit=TransactionalAuditWriter.from_session(session),
            )
            return None

    async def _cleanup_cancelled_preparation(
        self, *, actor: CurrentPrincipal, batch_id: UUID
    ) -> None:
        async with transaction(self._session_factory) as session:
            batches = BatchRepository(session)
            # The preparation worker takes this row lock before each chunk.
            # Waiting lets an in-flight chunk commit; CANCELLING stops the next one.
            batch = await batches.get(batch_id, for_update=True)
            if batch is None:
                return

            await self._delete_in_current_transaction(
                batch=batch,
                actor=actor,
                kg_units=KgRepository(session),
                batches=batches,
                audit=TransactionalAuditWriter.from_session(session),
            )

    def _ensure_deletable_basics(self, batch: Batch, *, actor: CurrentPrincipal) -> None:
        ensure_not_archived(batch)
        ensure_batch_edit_allowed(
            batch,
            actor=actor,
            now=self._clock(),
            edit_window=self._edit_window,
        )
        if batch.status is not BatchStatus.IN_PRODUCTION:
            raise BatchCannotBeDeletedError

    async def _delete_in_current_transaction(
        self,
        *,
        batch: Batch,
        actor: CurrentPrincipal,
        kg_units: KgRepository,
        batches: BatchRepository,
        audit: TransactionalAuditWriter,
    ) -> None:
        # Keep the legacy snapshot and transactional boundary intact.  The
        # cleanup path deliberately removes registered KG before its audit and
        # batch row; no post-commit deletion audit exists.
        await kg_units.delete_registered_for_batch(batch.id)
        await audit.record(
            actor=audit_actor(actor),
            action="batch.deleted",
            entity=batch_entity(batch),
            old_data={
                "production_order_id": str(batch.production_order_id)
                if batch.production_order_id
                else None,
                "name": batch.name,
                "description": batch.description,
                "planned_qty": batch.planned_qty,
                "day_plan_qty": batch.day_plan_qty,
                "status": batch.status.value,
            },
        )
        await batches.delete(batch)
