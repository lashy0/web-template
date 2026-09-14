from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, union
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.contexts.production.batches.commands import (
    AssignProductionOrder,
    CompleteBatch,
    CreateBatch,
    DeleteBatch,
    SetBatchArchived,
    UpdateBatch,
)
from app.contexts.production.batches.compat import LegacyKgUnitBridge
from app.contexts.production.batches.queries import BatchQueries, required_batch
from app.contexts.production.batches.repository import BatchRepository as NewBatchRepository
from app.contexts.production.compat.verification import LegacyVerificationHistoryAdapter
from app.contexts.production.kg.queries import KgQueries
from app.contexts.production.kg.repository import KgRepository
from app.contexts.production.preparation.commands.retry import RetryPreparation
from app.contexts.production.preparation.queries import PreparationQueries
from app.contexts.production.preparation.repository import PreparationRepository
from app.contexts.production.production_orders.queries import ProductionOrderQueries
from app.contexts.production.production_orders.repository import ProductionOrderRepository
from app.infrastructure.redis.preparation_notifier import RedisProgressNotifier
from app.modules.kg.models import KgState, KgUnit
from app.modules.verification.models import VerificationSession
from app.shared.security import CurrentPrincipal
from app.worker.preparation_dispatcher import CeleryWorkDispatcher

from ..exceptions import (
    BatchInvalidFiltersError,
)
from ..models import (
    Batch,
    BatchKeyGenerationJob,
    BatchReceipt,
    BatchShipment,
    BatchStatus,
)
from .lifecycle import BATCH_EDIT_WINDOW
from .transactions import transaction


class BatchService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window
        self._delete_batch = DeleteBatch(
            session_factory,
            verification_history=LegacyVerificationHistoryAdapter,
            notifier=RedisProgressNotifier(),
            edit_window=edit_window,
        )

    async def get(self, batch_id: UUID) -> Batch | None:
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), PreparationQueries(PreparationRepository(session))
            ).get(batch_id)

    async def get_key_generation_job(self, batch_id: UUID) -> BatchKeyGenerationJob | None:
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), PreparationQueries(PreparationRepository(session))
            ).get_preparation_job(batch_id)

    async def get_key_generation_jobs(
        self, batch_ids: Sequence[UUID]
    ) -> dict[UUID, BatchKeyGenerationJob]:
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), PreparationQueries(PreparationRepository(session))
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
        if production_order_id is not None and without_production_order:
            raise BatchInvalidFiltersError
        async with self._session_factory() as session:
            return await BatchQueries(
                NewBatchRepository(session), PreparationQueries(PreparationRepository(session))
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
                PreparationRepository(session),
                ProductionOrderQueries(ProductionOrderRepository(session)),
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

        await CeleryWorkDispatcher(self._session_factory, RedisProgressNotifier()).dispatch_after_commit(
            batch.id
        )

        return batch

    async def retry_preparation(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> Batch:
        async with transaction(self._session_factory) as session:
            batches = NewBatchRepository(session)
            batch = await required_batch(batches, batch_id, for_update=True)
            _, dispatched = await RetryPreparation(PreparationRepository(session)).execute(
                actor=actor, batch=batch
            )

        if dispatched:
            await CeleryWorkDispatcher(
                self._session_factory, RedisProgressNotifier()
            ).dispatch_after_commit(batch.id)

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
                ProductionOrderQueries(ProductionOrderRepository(session)),
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
                PreparationRepository(session),
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
        await self._delete_batch.execute(actor=actor, batch_id=batch_id)
