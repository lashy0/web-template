from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, union
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.contexts.production.batches.commands import (
    AssignProductionOrder,
    CompleteBatch,
    CreateBatch,
    SetBatchArchived,
    UpdateBatch,
)
from app.contexts.production.batches.compat import (
    LegacyKgUnitBridge,
    LegacyPreparationBridge,
    LegacyProductionOrderBridge,
    PreparationDispatcher,
)
from app.contexts.production.batches.queries import BatchQueries
from app.contexts.production.batches.repository import BatchRepository as NewBatchRepository
from app.contexts.production.kg.queries import KgQueries
from app.contexts.production.kg.repository import KgRepository
from app.modules.audit.service import AuditService
from app.modules.kg.models import KgState, KgUnit
from app.modules.kg.services import KgService
from app.modules.verification.models import VerificationSession
from app.modules.verification.services import VerificationManagementService
from app.shared.security import CurrentPrincipal

from ..exceptions import (
    BatchCannotBeDeletedError,
)
from ..models import (
    Batch,
    BatchKeyGenerationJob,
    BatchKeyGenerationStatus,
    BatchReceipt,
    BatchShipment,
    BatchStatus,
)
from ..repositories import (
    BatchReceiptRepository,
    BatchRepository,
    BatchShipmentRepository,
)
from . import audit, lifecycle, queries
from .key_generation import publish_preparation_status
from .lifecycle import BATCH_EDIT_WINDOW
from .transactions import transaction

GENERATE_BATCH_KEYS_TASK = "app.worker.generate_batch_keys"


class BatchService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window

    async def get(self, batch_id: UUID) -> Batch | None:
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), LegacyPreparationBridge(session)
            ).get(batch_id)

    async def get_key_generation_job(self, batch_id: UUID) -> BatchKeyGenerationJob | None:
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), LegacyPreparationBridge(session)
            ).get_preparation_job(batch_id)

    async def get_key_generation_jobs(
        self, batch_ids: Sequence[UUID]
    ) -> dict[UUID, BatchKeyGenerationJob]:
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), LegacyPreparationBridge(session)
            ).get_preparation_jobs(batch_ids)

    async def list(
        self,
        *,
        q: str | None,
        status: BatchStatus | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
        production_order_id: UUID | None = None,
        without_production_order: bool = False,
    ) -> tuple[list[Batch], int]:
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), LegacyPreparationBridge(session)
            ).list(
                q=q,
                status=status,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
                production_order_id=production_order_id,
                without_production_order=without_production_order,
            )

    async def deletion_availability(self, batches: Sequence[Batch]) -> dict[UUID, bool]:
        batch_ids = [batch.id for batch in batches]

        if not batch_ids:
            return {}

        async with self._session_factory() as session:
            activity_ids = set(
                (
                    await session.scalars(
                        union(
                            select(BatchReceipt.batch_id).where(
                                BatchReceipt.batch_id.in_(batch_ids)
                            ),
                            select(BatchShipment.batch_id).where(
                                BatchShipment.batch_id.in_(batch_ids)
                            ),
                            select(KgUnit.batch_id).where(
                                KgUnit.batch_id.in_(batch_ids),
                                KgUnit.state == KgState.SCRAPPED,
                            ),
                            select(KgUnit.batch_id)
                            .join(
                                VerificationSession,
                                VerificationSession.kg_dev_eui == KgUnit.dev_eui,
                            )
                            .where(KgUnit.batch_id.in_(batch_ids)),
                        )
                    )
                ).all()
            )

        return {
            batch.id: batch.status is BatchStatus.IN_PRODUCTION and batch.id not in activity_ids
            for batch in batches
        }

    async def preview_dev_eui_range(
        self,
        *,
        dev_eui_prefix: str,
        planned_qty: int,
    ) -> tuple[str, str]:
        async with self._session_factory() as session:
            return await KgQueries(KgRepository(session)).preview_allocation(
                dev_eui_prefix, planned_qty
            )

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
        activation_type: ActivationType,
        lorawan_version: LoRaWanVersion,
        kg_version_id: UUID | None = None,
        production_order_id: UUID | None = None,
    ) -> Batch:
        async with transaction(self._session_factory) as session:
            batch = await CreateBatch(
                NewBatchRepository(session),
                KgRepository(session),
                LegacyKgUnitBridge(session),
                LegacyPreparationBridge(session),
                LegacyProductionOrderBridge(session),
                TransactionalAuditWriter.from_session(session),
            ).execute(
                actor=actor,
                name=name,
                description=description,
                dev_eui_prefix=dev_eui_prefix,
                planned_qty=planned_qty,
                day_plan_qty=day_plan_qty,
                activation_type=activation_type,
                lorawan_version=lorawan_version,
                kg_version_id=kg_version_id,
                production_order_id=production_order_id,
            )

        await PreparationDispatcher(self._session_factory).dispatch_after_commit(batch.id)

        return batch

    async def retry_preparation(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> Batch:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batches = BatchRepository(session)
            batch = await queries.required_batch(batches, batch_id, for_update=True)
            lifecycle.ensure_not_archived(batch)

            job = await batches.get_key_generation_job(batch.id, for_update=True)

            if job is None or job.status is not BatchKeyGenerationStatus.FAILED:
                return batch

            await batches.update_key_generation_job(
                job,
                status=BatchKeyGenerationStatus.CREATING,
                progress=0,
                error_code=None,
            )

        await PreparationDispatcher(self._session_factory).dispatch_after_commit(batch.id)

        return batch

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        updates: Mapping[str, object],
    ) -> Batch:
        async with transaction(self._session_factory) as session:
            return await UpdateBatch(
                NewBatchRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, updates=updates)

    async def assign_production_order(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        production_order_id: UUID | None,
    ) -> Batch:
        async with transaction(self._session_factory) as session:
            return await AssignProductionOrder(
                NewBatchRepository(session),
                LegacyProductionOrderBridge(session),
                TransactionalAuditWriter.from_session(session),
            ).execute(actor=actor, batch_id=batch_id, production_order_id=production_order_id)

    async def complete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> Batch:
        async with transaction(self._session_factory) as session:
            return await CompleteBatch(
                NewBatchRepository(session),
                LegacyPreparationBridge(session),
                TransactionalAuditWriter.from_session(session),
            ).execute(actor=actor, batch_id=batch_id)

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        archived: bool,
    ) -> Batch:
        async with transaction(self._session_factory) as session:
            return await SetBatchArchived(
                NewBatchRepository(session), TransactionalAuditWriter.from_session(session)
            ).execute(actor=actor, batch_id=batch_id, archived=archived)

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> None:
        lifecycle.ensure_management_allowed(actor)

        preparation_cancelled = False
        preparation_progress = 0

        async with transaction(self._session_factory) as session:
            batch_repository = BatchRepository(session)
            receipt_repository = BatchReceiptRepository(session)
            shipment_repository = BatchShipmentRepository(session)
            kg_operations = KgService(session)

            batch = await queries.required_batch(
                batch_repository,
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_not_archived(batch)
            lifecycle.ensure_batch_edit_allowed(
                batch,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            if batch.status != BatchStatus.IN_PRODUCTION:
                raise BatchCannotBeDeletedError

            if await receipt_repository.exists_by_batch(batch.id):
                raise BatchCannotBeDeletedError

            if await shipment_repository.exists_by_batch(batch.id):
                raise BatchCannotBeDeletedError

            if await kg_operations.has_scrapped_units(batch.id):
                raise BatchCannotBeDeletedError

            if await VerificationManagementService.has_batch_history(session, batch.id):
                raise BatchCannotBeDeletedError

            job = await batch_repository.get_key_generation_job(batch.id, for_update=True)

            if job is not None and job.status is not BatchKeyGenerationStatus.READY:
                await batch_repository.update_key_generation_job(
                    job,
                    status=BatchKeyGenerationStatus.CANCELLING,
                    progress=job.progress,
                )
                preparation_progress = job.progress
                preparation_cancelled = True

            else:
                await AuditService.from_session(session).record(
                    actor=audit.audit_actor(actor),
                    action="batch.deleted",
                    entity=audit.batch_entity(batch),
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

                await kg_operations.delete_registered_for_batch(batch.id)
                await batch_repository.delete(batch)

        if not preparation_cancelled:
            return

        publish_preparation_status(
            batch_id,
            BatchKeyGenerationStatus.CANCELLING,
            preparation_progress,
        )

        # The worker observes CANCELLING under the same row lock before every chunk.
        # This waits out a chunk, then removes all partially-created KG data safely.
        async with transaction(self._session_factory) as session:
            batch_repository = BatchRepository(session)
            batch_for_cleanup = await batch_repository.get_by_id(batch_id, for_update=True)
            if batch_for_cleanup is None:
                return

            await KgService(session).delete_registered_for_batch(batch_for_cleanup.id)

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch.deleted",
                entity=audit.batch_entity(batch_for_cleanup),
                old_data={
                    "production_order_id": str(batch_for_cleanup.production_order_id)
                    if batch_for_cleanup.production_order_id
                    else None,
                    "name": batch_for_cleanup.name,
                    "description": batch_for_cleanup.description,
                    "planned_qty": batch_for_cleanup.planned_qty,
                    "day_plan_qty": batch_for_cleanup.day_plan_qty,
                    "status": batch_for_cleanup.status.value,
                },
            )

            await batch_repository.delete(batch_for_cleanup)
