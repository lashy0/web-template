from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.production_order.permissions import ProductionOrderPermission

from .exceptions import ProductionOrderNotFoundError
from .model import ProductionOrder
from .schemas import (
    CreateProductionOrderRequest,
    ProductionOrderListResponse,
    ProductionOrderResponse,
    UpdateProductionOrderArchivedRequest,
    UpdateProductionOrderRequest,
)
from .service import ProductionOrderManagementService

router = APIRouter(prefix="/production-orders", tags=["production_order"])


def _service(request: Request) -> ProductionOrderManagementService:
    return cast(ProductionOrderManagementService, request.app.state.production_order_management)


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
    items, total = await _service(request).list(
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
    service = _service(request)
    item = await service.get(order_id)
    if item is None:
        raise ProductionOrderNotFoundError
    batches_count, total_planned_qty = await service.get_totals(item.id)
    return _response(item, batches_count=batches_count, total_planned_qty=total_planned_qty)


@router.post("", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: CreateProductionOrderRequest,
    actor: Annotated[
        CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.CREATE))
    ],
    request: Request,
) -> ProductionOrderResponse:
    service = _service(request)
    item = await service.create(actor=actor, name=payload.name, description=payload.description)
    batches_count, total_planned_qty = await service.get_totals(item.id)
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
    service = _service(request)
    item = await service.update(
        order_id=order_id, actor=actor, updates=payload.model_dump(exclude_unset=True)
    )
    batches_count, total_planned_qty = await service.get_totals(item.id)
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
    service = _service(request)
    item = await service.set_archived(order_id=order_id, actor=actor, archived=payload.archived)
    batches_count, total_planned_qty = await service.get_totals(item.id)
    return _response(item, batches_count=batches_count, total_planned_qty=total_planned_qty)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    actor: Annotated[
        CurrentPrincipalDep, Depends(require_permission(ProductionOrderPermission.DELETE))
    ],
    request: Request,
) -> None:
    await _service(request).delete(order_id=order_id, actor=actor)
