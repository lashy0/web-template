from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..exceptions import KgNotFoundError
from ..models import KgStatus
from ..permissions import KgPermission
from ..schemas import DevEui, KgBatchListResponse, KgListResponse, KgResponse
from .common import _batch_list_item_response, _response, _service

router = APIRouter()


@router.get("/batch/{batch_id}", response_model=KgBatchListResponse)
async def list_kg_by_batch(
    batch_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(KgPermission.READ)),
    ],
    request: Request,
    q: str | None = None,
    status: KgStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> KgBatchListResponse:
    items, total = await _service(request).list_batch_items(
        batch_id,
        page=page,
        page_size=page_size,
        q=q,
        status=status,
    )

    return KgBatchListResponse(
        items=[_batch_list_item_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("", response_model=KgListResponse)
async def list_kg(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(KgPermission.READ)),
    ],
    request: Request,
    q: str | None = None,
    batch_id: UUID | None = None,
    status: KgStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "dev_eui",
        "batch_id",
        "status",
        "created_at",
        "updated_at",
    ] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> KgListResponse:
    kg_units, total = await _service(request).list(
        q=q,
        batch_id=batch_id,
        status=status,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return KgListResponse(
        items=[_response(kg) for kg in kg_units],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{dev_eui}", response_model=KgResponse)
async def get_kg(
    dev_eui: DevEui,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(KgPermission.READ)),
    ],
    request: Request,
) -> KgResponse:
    kg = await _service(request).get(dev_eui=dev_eui)

    if kg is None:
        raise KgNotFoundError

    return _response(kg)
