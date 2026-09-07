from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..exceptions import BatchNotFoundError
from ..models import BatchStatus
from ..permissions import BatchPermission
from ..schemas import (
    BatchListResponse,
    BatchResponse,
    CreateBatchRequest,
    UpdateBatchArchivedRequest,
    UpdateBatchRequest,
)
from .common import _batch_response, _service

router = APIRouter(prefix="/batches", tags=["batch"])


@router.get("/", response_model=BatchListResponse)
async def list_batches(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.READ)),
    ],
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
) -> BatchListResponse:
    batches, total = await _service(request).list(
        q=q,
        status=status_filter,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return BatchListResponse(
        items=[_batch_response(batch) for batch in batches],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.READ)),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).get(batch_id)

    if batch is None:
        raise BatchNotFoundError

    return _batch_response(batch)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: CreateBatchRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.CREATE)),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).create(
        actor=principal,
        name=payload.name,
        description=payload.description,
        dev_eui_prefix=payload.dev_eui_prefix,
        planned_qty=payload.planned_qty,
        day_plan_qty=payload.day_plan_qty,
    )

    return _batch_response(batch)


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    payload: UpdateBatchRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.UPDATE)),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).update(
        actor=principal,
        batch_id=batch_id,
        updates=payload.model_dump(exclude_unset=True),
    )

    return _batch_response(batch)


@router.put("/{batch_id}/archived", response_model=BatchResponse)
async def update_batch_archived(
    batch_id: UUID,
    payload: UpdateBatchArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.ARCHIVE)),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).set_archived(
        actor=principal,
        batch_id=batch_id,
        archived=payload.archived,
    )

    return _batch_response(batch)


@router.post("/{batch_id}/complete", response_model=BatchResponse)
async def complete_batch(
    batch_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.COMPLETE)),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).complete(
        actor=principal,
        batch_id=batch_id,
    )

    return _batch_response(batch)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.DELETE)),
    ],
    request: Request,
) -> None:
    await _service(request).delete(
        actor=principal,
        batch_id=batch_id,
    )
