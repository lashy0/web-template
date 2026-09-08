from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..permissions import KgPermission
from ..schemas import (
    CreateKgDevEuiPrefixRequest,
    DevEuiPrefix,
    KgDevEuiPrefixListResponse,
    KgDevEuiPrefixResponse,
    UpdateKgDevEuiPrefixArchivedRequest,
    UpdateKgDevEuiPrefixRequest,
)
from .common import _prefix_response, _prefix_service

router = APIRouter()


@router.get(
    "/dev-eui-prefixes",
    response_model=KgDevEuiPrefixListResponse,
)
async def list_dev_eui_prefixes(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(KgPermission.PREFIX_READ)),
    ],
    request: Request,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "prefix",
        "name",
        "short_code",
        "created_at",
        "archived_at",
    ] = "prefix",
    order: Literal["asc", "desc"] = "asc",
) -> KgDevEuiPrefixListResponse:
    items, total = await _prefix_service(request).list(
        q=q,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return KgDevEuiPrefixListResponse(
        items=[
            _prefix_response(item, batch_count=batch_count)
            for item, batch_count in items
        ],
        total=total,
        page=page,
        page_size=page_size,
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
        Depends(require_permission(KgPermission.PREFIX_CREATE)),
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
        Depends(require_permission(KgPermission.PREFIX_UPDATE)),
    ],
    request: Request,
) -> KgDevEuiPrefixResponse:
    item = await _prefix_service(request).update(
        actor=principal,
        prefix=prefix,
        updates=payload.model_dump(exclude_unset=True),
    )

    return _prefix_response(item)


@router.put(
    "/dev-eui-prefixes/{prefix}/archived",
    response_model=KgDevEuiPrefixResponse,
)
async def update_dev_eui_prefix_archived(
    prefix: DevEuiPrefix,
    payload: UpdateKgDevEuiPrefixArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(KgPermission.PREFIX_ARCHIVE)),
    ],
    request: Request,
) -> KgDevEuiPrefixResponse:
    item = await _prefix_service(request).set_archived(
        actor=principal,
        prefix=prefix,
        archived=payload.archived,
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
        Depends(require_permission(KgPermission.PREFIX_DELETE)),
    ],
    request: Request,
) -> None:
    await _prefix_service(request).delete(
        actor=principal,
        prefix=prefix,
    )
