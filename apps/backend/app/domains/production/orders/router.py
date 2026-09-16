from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.audit.writer import TransactionalAuditWriter

from .commands import (
    CreateProductionOrder,
    DeleteProductionOrder,
    SetProductionOrderArchived,
    UpdateProductionOrder,
)
from .exceptions import ProductionOrderNotFoundError
from .model import ProductionOrder
from .permissions import ProductionOrderPermission
from .queries import ProductionOrderQueries
from .repository import ProductionOrderRepository
from .schemas import (
    CreateProductionOrderRequest,
    ProductionOrderListResponse,
    ProductionOrderResponse,
    UpdateProductionOrderArchivedRequest,
    UpdateProductionOrderRequest,
)

router = APIRouter(prefix="/production-orders", tags=["production_order"])


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


@asynccontextmanager
async def _transaction(request: Request) -> AsyncIterator[AsyncSession]:
    async with _session_factory(request)() as session, session.begin():
        yield session


def _response(
    item: ProductionOrder, *, batches_count: int, total_planned_qty: int
) -> ProductionOrderResponse:
    return ProductionOrderResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        created_at=item.created_at,
        updated_at=item.updated_at,
        archived_at=item.archived_at,
        batches_count=batches_count,
        total_planned_qty=total_planned_qty,
    )


@router.get("/", response_model=ProductionOrderListResponse)
async def list_orders(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.READ))],
    request: Request,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "name", "created_at", "updated_at", "archived_at", "batches_count", "total_planned_qty"
    ] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> ProductionOrderListResponse:
    async with _session_factory(request)() as session:
        items, total = await ProductionOrderQueries(ProductionOrderRepository(session)).list(
            q=q, archived=archived, page=page, page_size=page_size, sort=sort, order=order
        )
    return ProductionOrderListResponse(
        items=[
            _response(item, batches_count=count, total_planned_qty=quantity)
            for item, count, quantity in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_id}", response_model=ProductionOrderResponse)
async def get_order(
    order_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.READ))],
    request: Request,
) -> ProductionOrderResponse:
    async with _session_factory(request)() as session:
        queries = ProductionOrderQueries(ProductionOrderRepository(session))
        item = await queries.get(order_id)
        batches_count, total_planned_qty = (
            await queries.totals(order_id) if item is not None else (0, 0)
        )
    if item is None:
        raise ProductionOrderNotFoundError
    return _response(item, batches_count=batches_count, total_planned_qty=total_planned_qty)


@router.post("", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: CreateProductionOrderRequest,
    actor: Annotated[
        CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.CREATE))
    ],
    request: Request,
) -> ProductionOrderResponse:
    async with _transaction(request) as session:
        repository = ProductionOrderRepository(session)
        item = await CreateProductionOrder(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(actor=actor, name=payload.name, description=payload.description)
        batches_count, total_planned_qty = await ProductionOrderQueries(repository).totals(item.id)
    return _response(item, batches_count=batches_count, total_planned_qty=total_planned_qty)


@router.patch("/{order_id}", response_model=ProductionOrderResponse)
async def update_order(
    order_id: UUID,
    payload: UpdateProductionOrderRequest,
    actor: Annotated[
        CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.UPDATE))
    ],
    request: Request,
) -> ProductionOrderResponse:
    async with _transaction(request) as session:
        repository = ProductionOrderRepository(session)
        item = await UpdateProductionOrder(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(order_id=order_id, actor=actor, updates=payload.model_dump(exclude_unset=True))
        batches_count, total_planned_qty = await ProductionOrderQueries(repository).totals(item.id)
    return _response(item, batches_count=batches_count, total_planned_qty=total_planned_qty)


@router.put("/{order_id}/archived", response_model=ProductionOrderResponse)
async def archive_order(
    order_id: UUID,
    payload: UpdateProductionOrderArchivedRequest,
    actor: Annotated[
        CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.ARCHIVE))
    ],
    request: Request,
) -> ProductionOrderResponse:
    async with _transaction(request) as session:
        repository = ProductionOrderRepository(session)
        item = await SetProductionOrderArchived(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(order_id=order_id, actor=actor, archived=payload.archived)
        batches_count, total_planned_qty = await ProductionOrderQueries(repository).totals(item.id)
    return _response(item, batches_count=batches_count, total_planned_qty=total_planned_qty)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    actor: Annotated[
        CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.DELETE))
    ],
    request: Request,
) -> None:
    async with _transaction(request) as session:
        await DeleteProductionOrder(
            ProductionOrderRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(order_id=order_id, actor=actor)
