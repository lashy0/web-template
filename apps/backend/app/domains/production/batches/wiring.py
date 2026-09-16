from collections.abc import Callable
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.domains.production.contracts import VerificationHistoryPort
from app.domains.production.kg.queries import KgQueries
from app.domains.production.kg.repository import KgRepository
from app.domains.production.orders.queries import ProductionOrderQueries
from app.domains.production.orders.repository import ProductionOrderRepository
from app.domains.production.preparation.commands.retry import RetryPreparation
from app.domains.production.preparation.queries import PreparationQueries
from app.domains.production.preparation.repository import PreparationRepository
from app.shared.uow import PostCommitExecutor, UnitOfWork

from .commands import (
    AssignProductionOrder,
    CompleteBatch,
    CreateBatch,
    DeleteBatch,
    SetBatchArchived,
    UpdateBatch,
)
from .model import Batch
from .queries import BatchQueries
from .repository import BatchRepository


def get_verification_history_factory(
    request: Request,
) -> Callable[[AsyncSession], VerificationHistoryPort]:
    return cast(
        Callable[[AsyncSession], VerificationHistoryPort],
        request.app.state.production_verification_history_factory,
    )


def get_post_commit_executor(request: Request) -> PostCommitExecutor:
    return cast(PostCommitExecutor, request.app.state.post_commit_executor)


VerificationHistoryFactoryDep = Annotated[
    Callable[[AsyncSession], VerificationHistoryPort], Depends(get_verification_history_factory)
]
PostCommitExecutorDep = Annotated[PostCommitExecutor, Depends(get_post_commit_executor)]


def create_queries(session: AsyncSession) -> BatchQueries:
    return BatchQueries(
        BatchRepository(session), PreparationQueries(PreparationRepository(session))
    )


def create_preview_queries(session: AsyncSession) -> KgQueries:
    return KgQueries(KgRepository(session))


def create_batch_command(session: AsyncSession, uow: UnitOfWork) -> CreateBatch:
    return CreateBatch(
        repository=BatchRepository(session),
        kg_repository=KgRepository(session),
        preparation=PreparationRepository(session),
        orders=ProductionOrderQueries(ProductionOrderRepository(session)),
        audit=TransactionalAuditWriter.from_session(session),
        uow=uow,
    )


def update_batch_command(session: AsyncSession) -> UpdateBatch:
    return UpdateBatch(BatchRepository(session), TransactionalAuditWriter.from_session(session))


def set_batch_archived_command(session: AsyncSession) -> SetBatchArchived:
    return SetBatchArchived(
        BatchRepository(session), TransactionalAuditWriter.from_session(session)
    )


def complete_batch_command(session: AsyncSession) -> CompleteBatch:
    return CompleteBatch(
        BatchRepository(session),
        PreparationRepository(session),
        TransactionalAuditWriter.from_session(session),
    )


def retry_preparation_command(session: AsyncSession, uow: UnitOfWork) -> RetryPreparation:
    return RetryPreparation(PreparationRepository(session), uow)


def delete_batch_command(
    session_factory: async_sessionmaker[AsyncSession],
    verification_history: Callable[[AsyncSession], VerificationHistoryPort],
    effect_executor: PostCommitExecutor,
) -> DeleteBatch:
    return DeleteBatch(
        session_factory,
        verification_history=verification_history,
        effect_executor=effect_executor,
    )


def assign_production_order_command(session: AsyncSession) -> AssignProductionOrder:
    return AssignProductionOrder(
        BatchRepository(session),
        ProductionOrderQueries(ProductionOrderRepository(session)),
        TransactionalAuditWriter.from_session(session),
    )


async def required_batch_for_update(session: AsyncSession, batch_id: UUID) -> Batch:
    from .queries import required_batch

    return await required_batch(BatchRepository(session), batch_id, for_update=True)
