from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..permissions import KgPermission
from ..schemas import (
    CreateKgDevEuiPrefixRequest,
    DevEuiPrefix,
    KgDevEuiPrefixListResponse,
    KgDevEuiPrefixResponse,
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
) -> KgDevEuiPrefixListResponse:
    items = await _prefix_service(request).list()

    return KgDevEuiPrefixListResponse(
        items=[_prefix_response(item) for item in items],
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
