# mypy: disable-error-code=untyped-decorator

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains.production.orders.schemas import AssignProductionOrderRequest
from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission
from app.shared.uow import PostCommitExecutor, UnitOfWork, transaction

from ..exceptions import BatchNotFoundError
from .model import Batch, BatchStatus
from .permissions import BatchPermission
from .presentation import batch_response
from .schemas import (
    BatchListResponse,
    BatchResponse,
    CreateBatchRequest,
    DevEuiRangePreviewResponse,
    UpdateBatchArchivedRequest,
    UpdateBatchRequest,
)
from .wiring import (
    PostCommitExecutorDep,
    VerificationHistoryFactoryDep,
    assign_production_order_command,
    complete_batch_command,
    create_batch_command,
    create_preview_queries,
    create_queries,
    delete_batch_command,
    required_batch_for_update,
    retry_preparation_command,
    set_batch_archived_command,
    update_batch_command,
)

router = APIRouter(prefix="/batches", tags=["batch"])


@asynccontextmanager
async def _transaction(
    factory: async_sessionmaker[AsyncSession], executor: PostCommitExecutor
) -> AsyncIterator[UnitOfWork]:
    async with transaction(factory, executor=executor) as uow:
        yield uow


async def _response(
    session: AsyncSession, batch: Batch, verification_history_factory: VerificationHistoryFactoryDep
) -> BatchResponse:
    queries = create_queries(session)
    can_delete = (
        await queries.deletion_availability([batch], verification_history_factory(session))
    )[batch.id]
    return batch_response(
        batch, can_delete=can_delete, job=await queries.get_preparation_job(batch.id)
    )


@router.get("/dev-eui-range-preview", response_model=DevEuiRangePreviewResponse)
async def preview_dev_eui_range(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.CREATE))],
    session_factory: SessionFactoryDep,
    dev_eui_prefix: str,
    planned_qty: int = Query(gt=0),
) -> DevEuiRangePreviewResponse:
    async with session_factory() as session:
        first, last = await create_preview_queries(session).preview_allocation(
            dev_eui_prefix, planned_qty
        )
    return DevEuiRangePreviewResponse(first_dev_eui=first, last_dev_eui=last)


@router.get("/", response_model=BatchListResponse)
async def list_batches(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    session_factory: SessionFactoryDep,
    verification_history_factory: VerificationHistoryFactoryDep,
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
    async with session_factory() as session:
        queries = create_queries(session)
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
            batches, verification_history_factory(session)
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
    session_factory: SessionFactoryDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> BatchResponse:
    async with session_factory() as session:
        batch = await create_queries(session).get(batch_id)
        if batch is None:
            raise BatchNotFoundError
        return await _response(session, batch, verification_history_factory)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: CreateBatchRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.CREATE))],
    session_factory: SessionFactoryDep,
    executor: PostCommitExecutorDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> BatchResponse:
    async with _transaction(session_factory, executor) as uow:
        session = uow.session
        batch = await create_batch_command(session, uow).execute(
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
        response = await _response(session, batch, verification_history_factory)
    return response


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    payload: UpdateBatchRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.UPDATE))],
    session_factory: SessionFactoryDep,
    executor: PostCommitExecutorDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> BatchResponse:
    async with _transaction(session_factory, executor) as uow:
        session = uow.session
        batch = await update_batch_command(session).execute(
            actor=principal, batch_id=batch_id, updates=payload.model_dump(exclude_unset=True)
        )
        return await _response(session, batch, verification_history_factory)


@router.put("/{batch_id}/archived", response_model=BatchResponse)
async def update_batch_archived(
    batch_id: UUID,
    payload: UpdateBatchArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.ARCHIVE))],
    session_factory: SessionFactoryDep,
    executor: PostCommitExecutorDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> BatchResponse:
    async with _transaction(session_factory, executor) as uow:
        session = uow.session
        batch = await set_batch_archived_command(session).execute(
            actor=principal, batch_id=batch_id, archived=payload.archived
        )
        return await _response(session, batch, verification_history_factory)


@router.post("/{batch_id}/complete", response_model=BatchResponse)
async def complete_batch(
    batch_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.COMPLETE))
    ],
    session_factory: SessionFactoryDep,
    executor: PostCommitExecutorDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> BatchResponse:
    async with _transaction(session_factory, executor) as uow:
        session = uow.session
        batch = await complete_batch_command(session).execute(actor=principal, batch_id=batch_id)
        return await _response(session, batch, verification_history_factory)


@router.post("/{batch_id}/preparation/retry", response_model=BatchResponse)
async def retry_batch_preparation(
    batch_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.UPDATE))],
    session_factory: SessionFactoryDep,
    executor: PostCommitExecutorDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> BatchResponse:
    async with _transaction(session_factory, executor) as uow:
        session = uow.session
        batch = await required_batch_for_update(session, batch_id)
        await retry_preparation_command(session, uow).execute(actor=principal, batch=batch)
        response = await _response(session, batch, verification_history_factory)
    return response


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.DELETE))],
    session_factory: SessionFactoryDep,
    executor: PostCommitExecutorDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> None:
    await delete_batch_command(session_factory, verification_history_factory, executor).execute(
        actor=principal, batch_id=batch_id
    )


@router.put("/{batch_id}/production-order", response_model=BatchResponse)
async def assign_production_order(
    batch_id: UUID,
    payload: AssignProductionOrderRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.ASSIGN_PRODUCTION_ORDER))
    ],
    session_factory: SessionFactoryDep,
    executor: PostCommitExecutorDep,
    verification_history_factory: VerificationHistoryFactoryDep,
) -> BatchResponse:
    async with _transaction(session_factory, executor) as uow:
        session = uow.session
        batch = await assign_production_order_command(session).execute(
            actor=principal, batch_id=batch_id, production_order_id=payload.production_order_id
        )
        return await _response(session, batch, verification_history_factory)
