# mypy: disable-error-code=untyped-decorator

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.batch.exceptions import BatchNotFoundError
from app.modules.batch.permissions import BatchPermission
from app.modules.batch.routers.common import _batch_response, _service
from app.modules.kg.schemas import DevEuiPrefix
from app.modules.production_order.schemas import AssignProductionOrderRequest

from .model import BatchStatus
from .schemas import (
    BatchListResponse,
    BatchResponse,
    CreateBatchRequest,
    DevEuiRangePreviewResponse,
    UpdateBatchArchivedRequest,
    UpdateBatchRequest,
)

router = APIRouter(prefix="/batches", tags=["batch"])


@router.get("/dev-eui-range-preview", response_model=DevEuiRangePreviewResponse)
async def preview_dev_eui_range(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.CREATE))],
    request: Request,
    dev_eui_prefix: DevEuiPrefix,
    planned_qty: int = Query(gt=0),
) -> DevEuiRangePreviewResponse:
    first, last = await _service(request).preview_dev_eui_range(
        dev_eui_prefix=dev_eui_prefix, planned_qty=planned_qty
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
    batches, total = await _service(request).list(
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
    deletion_availability = await _service(request).deletion_availability(batches)
    jobs = await _service(request).get_key_generation_jobs([batch.id for batch in batches])
    return BatchListResponse(
        items=[
            await _batch_response(
                request, batch, can_delete=deletion_availability[batch.id], job=jobs.get(batch.id)
            )
            for batch in batches
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).get(batch_id)
    if batch is None:
        raise BatchNotFoundError
    return await _batch_response(request, batch)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: CreateBatchRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.CREATE))],
    request: Request,
) -> BatchResponse:
    create_args = {
        "actor": principal,
        "name": payload.name,
        "description": payload.description,
        "dev_eui_prefix": payload.dev_eui_prefix,
        "planned_qty": payload.planned_qty,
        "day_plan_qty": payload.day_plan_qty,
        "activation_type": payload.lorawan_config.activation_type,
        "lorawan_version": payload.lorawan_config.lorawan_version,
        "production_order_id": payload.production_order_id,
    }
    if payload.kg_version_id is not None:
        create_args["kg_version_id"] = payload.kg_version_id
    batch = await _service(request).create(**create_args)
    return await _batch_response(request, batch)


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    payload: UpdateBatchRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.UPDATE))],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).update(
        actor=principal, batch_id=batch_id, updates=payload.model_dump(exclude_unset=True)
    )
    return await _batch_response(request, batch)


@router.put("/{batch_id}/archived", response_model=BatchResponse)
async def update_batch_archived(
    batch_id: UUID,
    payload: UpdateBatchArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.ARCHIVE))],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).set_archived(
        actor=principal, batch_id=batch_id, archived=payload.archived
    )
    return await _batch_response(request, batch)


@router.post("/{batch_id}/complete", response_model=BatchResponse)
async def complete_batch(
    batch_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.COMPLETE))
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).complete(actor=principal, batch_id=batch_id)
    return await _batch_response(request, batch)


@router.post("/{batch_id}/preparation/retry", response_model=BatchResponse)
async def retry_batch_preparation(
    batch_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.UPDATE))],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).retry_preparation(actor=principal, batch_id=batch_id)
    return await _batch_response(request, batch)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.DELETE))],
    request: Request,
) -> None:
    await _service(request).delete(actor=principal, batch_id=batch_id)


@router.put("/{batch_id}/production-order", response_model=BatchResponse)
async def assign_production_order(
    batch_id: UUID,
    payload: AssignProductionOrderRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.ASSIGN_PRODUCTION_ORDER))
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).assign_production_order(
        actor=principal, batch_id=batch_id, production_order_id=payload.production_order_id
    )
    return await _batch_response(request, batch)
