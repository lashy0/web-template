# mypy: disable-error-code=untyped-decorator

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.domains.production.kg.queries import KgQueries
from app.domains.production.kg.repository import KgRepository
from app.domains.production.orders.queries import ProductionOrderQueries
from app.domains.production.orders.repository import ProductionOrderRepository
from app.domains.production.orders.schemas import AssignProductionOrderRequest
from app.domains.production.preparation.commands.retry import RetryPreparation
from app.domains.production.preparation.queries import PreparationQueries
from app.domains.production.preparation.repository import PreparationRepository
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission
from app.shared.uow import PostCommitExecutor, UnitOfWork, transaction

from ..contracts import VerificationHistoryPort
from ..exceptions import BatchNotFoundError
from .commands import (
    AssignProductionOrder,
    CompleteBatch,
    CreateBatch,
    DeleteBatch,
    SetBatchArchived,
    UpdateBatch,
)
from .model import Batch, BatchStatus
from .permissions import BatchPermission
from .presentation import batch_response
from .queries import BatchQueries, required_batch
from .repository import BatchRepository
from .schemas import (
    BatchListResponse,
    BatchResponse,
    CreateBatchRequest,
    DevEuiRangePreviewResponse,
    UpdateBatchArchivedRequest,
    UpdateBatchRequest,
)

router = APIRouter(prefix="/batches", tags=["batch"])


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


def _verification_history(request: Request, session: AsyncSession) -> VerificationHistoryPort:
    factory = cast(
        Callable[[AsyncSession], VerificationHistoryPort],
        request.app.state.production_verification_history_factory,
    )
    return factory(session)


@asynccontextmanager
async def _transaction(request: Request) -> AsyncIterator[UnitOfWork]:
    executor = cast(PostCommitExecutor, request.app.state.post_commit_executor)
    async with transaction(_session_factory(request), executor=executor) as uow:
        yield uow


async def _response(request: Request, session: AsyncSession, batch: Batch) -> BatchResponse:
    queries = BatchQueries(
        BatchRepository(session), PreparationQueries(PreparationRepository(session))
    )
    can_delete = (
        await queries.deletion_availability([batch], _verification_history(request, session))
    )[batch.id]
    return batch_response(
        batch, can_delete=can_delete, job=await queries.get_preparation_job(batch.id)
    )


@router.get("/dev-eui-range-preview", response_model=DevEuiRangePreviewResponse)
async def preview_dev_eui_range(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.CREATE))],
    request: Request,
    dev_eui_prefix: str,
    planned_qty: int = Query(gt=0),
) -> DevEuiRangePreviewResponse:
    async with _session_factory(request)() as session:
        first, last = await KgQueries(KgRepository(session)).preview_allocation(
            dev_eui_prefix, planned_qty
        )
    return DevEuiRangePreviewResponse(first_dev_eui=first, last_dev_eui=last)


@router.get("/", response_model=BatchListResponse)
async def list_batches(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    request: Request,
    q: str | None = None,
    status_filter: BatchStatus | None = Query(default=None, alias="status"),
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "name",
        "planned_qty",
        "day_plan_qty",
        "status",
        "created_at",
        "updated_at",
        "completed_at",
        "archived_at",
    ] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    production_order_id: UUID | None = None,
    without_production_order: bool = False,
) -> BatchListResponse:
    async with _session_factory(request)() as session:
        queries = BatchQueries(
            BatchRepository(session), PreparationQueries(PreparationRepository(session))
        )
        batches, total = await queries.list(
            q=q,
            status=status_filter,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            production_order_id=production_order_id,
            without_production_order=without_production_order,
        )
        availability = await queries.deletion_availability(
            batches, _verification_history(request, session)
        )
        jobs = await queries.get_preparation_jobs([batch.id for batch in batches])
        items = [
            batch_response(batch, can_delete=availability[batch.id], job=jobs.get(batch.id))
            for batch in batches
        ]
    return BatchListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    request: Request,
) -> BatchResponse:
    async with _session_factory(request)() as session:
        batch = await BatchQueries(
            BatchRepository(session), PreparationQueries(PreparationRepository(session))
        ).get(batch_id)
        if batch is None:
            raise BatchNotFoundError
        return await _response(request, session, batch)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: CreateBatchRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.CREATE))],
    request: Request,
) -> BatchResponse:
    async with _transaction(request) as uow:
        session = uow.session
        batch = await CreateBatch(
            BatchRepository(session),
            KgRepository(session),
            PreparationRepository(session),
            ProductionOrderQueries(ProductionOrderRepository(session)),
            TransactionalAuditWriter.from_session(session),
            uow,
        ).execute(
            actor=principal,
            name=payload.name,
            description=payload.description,
            dev_eui_prefix=payload.dev_eui_prefix,
            planned_qty=payload.planned_qty,
            day_plan_qty=payload.day_plan_qty,
            activation_type=payload.lorawan_config.activation_type,
            lorawan_version=payload.lorawan_config.lorawan_version,
            kg_version_id=payload.kg_version_id,
            production_order_id=payload.production_order_id,
        )
        response = await _response(request, session, batch)
    return response


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    payload: UpdateBatchRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.UPDATE))],
    request: Request,
) -> BatchResponse:
    async with _transaction(request) as uow:
        session = uow.session
        batch = await UpdateBatch(
            BatchRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(
            actor=principal, batch_id=batch_id, updates=payload.model_dump(exclude_unset=True)
        )
        return await _response(request, session, batch)


@router.put("/{batch_id}/archived", response_model=BatchResponse)
async def update_batch_archived(
    batch_id: UUID,
    payload: UpdateBatchArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.ARCHIVE))],
    request: Request,
) -> BatchResponse:
    async with _transaction(request) as uow:
        session = uow.session
        batch = await SetBatchArchived(
            BatchRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, batch_id=batch_id, archived=payload.archived)
        return await _response(request, session, batch)


@router.post("/{batch_id}/complete", response_model=BatchResponse)
async def complete_batch(
    batch_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.COMPLETE))
    ],
    request: Request,
) -> BatchResponse:
    async with _transaction(request) as uow:
        session = uow.session
        batch = await CompleteBatch(
            BatchRepository(session),
            PreparationRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(actor=principal, batch_id=batch_id)
        return await _response(request, session, batch)


@router.post("/{batch_id}/preparation/retry", response_model=BatchResponse)
async def retry_batch_preparation(
    batch_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.UPDATE))],
    request: Request,
) -> BatchResponse:
    async with _transaction(request) as uow:
        session = uow.session
        batch = await required_batch(BatchRepository(session), batch_id, for_update=True)
        await RetryPreparation(PreparationRepository(session), uow).execute(
            actor=principal, batch=batch
        )
        response = await _response(request, session, batch)
    return response


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.DELETE))],
    request: Request,
) -> None:
    await DeleteBatch(
        _session_factory(request),
        verification_history=cast(
            Callable[[AsyncSession], VerificationHistoryPort],
            request.app.state.production_verification_history_factory,
        ),
        effect_executor=cast(PostCommitExecutor, request.app.state.post_commit_executor),
    ).execute(actor=principal, batch_id=batch_id)


@router.put("/{batch_id}/production-order", response_model=BatchResponse)
async def assign_production_order(
    batch_id: UUID,
    payload: AssignProductionOrderRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.ASSIGN_PRODUCTION_ORDER))
    ],
    request: Request,
) -> BatchResponse:
    async with _transaction(request) as uow:
        session = uow.session
        batch = await AssignProductionOrder(
            BatchRepository(session),
            ProductionOrderQueries(ProductionOrderRepository(session)),
            TransactionalAuditWriter.from_session(session),
        ).execute(
            actor=principal, batch_id=batch_id, production_order_id=payload.production_order_id
        )
        return await _response(request, session, batch)
