from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.kg.exceptions import KgNotFoundError
from app.modules.kg.models import KgStatus, KgUnit, KgDevEuiPrefix
from app.modules.kg.permissions import KgPermission
from app.modules.kg.schemas import (
    CreateKgDevEuiPrefixRequest,
    DevEui,
    DevEuiPrefix,
    KgDevEuiPrefixListResponse,
    KgDevEuiPrefixResponse,
    KgListResponse,
    KgResponse,
    UpdateKgDevEuiPrefixRequest,
)
from app.modules.kg.service import KgManagementService, KgDevEuiPrefixManagementService

router = APIRouter(prefix="/kg", tags=["kg"])


def _response(kg: KgUnit) -> KgResponse:
    return KgResponse(
        dev_eui=kg.dev_eui,
        short_id=kg.short_id,
        batch_id=kg.batch_id,
        status=kg.status,
        created_at=kg.created_at,
        updated_at=kg.updated_at,
    )


def _prefix_response(item: KgDevEuiPrefix) -> KgDevEuiPrefixResponse:
    return KgDevEuiPrefixResponse(
        prefix=item.prefix,
        short_code=item.short_code,
        name=item.name,
        created_at=item.created_at,
    )


def _service(request: Request) -> KgManagementService:
    return cast(KgManagementService, request.app.state.kg_management)


def _prefix_service(request: Request) -> KgDevEuiPrefixManagementService:
    return cast(KgDevEuiPrefixManagementService, request.app.state.kg_dev_eui_prefix_management)


@router.get("", response_model=KgListResponse)
async def list_kg(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.READ))],
    request: Request,
    q: str | None = None,
    batch_id: UUID | None = None,
    status: KgStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["dev_eui", "batch_id", "status", "created_at", "updated_at"] = "created_at",
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


@router.get(
    "/dev-eui-prefixes",
    response_model=KgDevEuiPrefixListResponse,
)
async def list_dev_eui_prefixes(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                KgPermission.PREFIX_READ
            )
        ),
    ],
    request: Request,
) -> KgDevEuiPrefixListResponse:
    items = await _prefix_service(request).list()

    return KgDevEuiPrefixListResponse(
        items=[
            _prefix_response(item)
            for item in items
        ],
        total=len(items),
    )


@router.post(
    "/dev-eui-prefixes",
    response_model=KgDevEuiPrefixResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dev_eui_prefix(
    payload: CreateKgDevEuiPrefixRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                KgPermission.PREFIX_CREATE
            )
        ),
    ],
    request: Request,
) -> KgDevEuiPrefixResponse:
    item = await _prefix_service(request).create(
        actor=principal,
        prefix=payload.prefix,
        short_code=payload.short_code,
        name=payload.name,
    )

    return _prefix_response(item)


@router.patch(
    "/dev-eui-prefixes/{prefix}",
    response_model=KgDevEuiPrefixResponse,
)
async def update_dev_eui_prefix(
    prefix: DevEuiPrefix,
    payload: UpdateKgDevEuiPrefixRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                KgPermission.PREFIX_UPDATE
            )
        ),
    ],
    request: Request,
) -> KgDevEuiPrefixResponse:
    item = await _prefix_service(request).update(
        actor=principal,
        prefix=prefix,
        updates=payload.model_dump(
            exclude_unset=True
        ),
    )

    return _prefix_response(item)


@router.delete(
    "/dev-eui-prefixes/{prefix}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_dev_eui_prefix(
    prefix: DevEuiPrefix,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                KgPermission.PREFIX_DELETE
            )
        ),
    ],
    request: Request,
) -> None:
    await _prefix_service(request).delete(
        actor=principal,
        prefix=prefix,
    )


@router.get("/{dev_eui}", response_model=KgResponse)
async def get_kg(
    dev_eui: DevEui,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.READ))],
    request: Request,
) -> KgResponse:
    kg = await _service(request).get(dev_eui=dev_eui)

    if kg is None:
        raise KgNotFoundError

    return _response(kg)
