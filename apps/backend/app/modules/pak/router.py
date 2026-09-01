from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.pak.exceptions import PakNotFoundError
from app.modules.pak.models import PakDevice, PakDeviceKind
from app.modules.pak.permissions import PakPermission
from app.modules.pak.schemas import (
    CreatePakDeviceRequest,
    CreatePakDeviceResponse,
    PakAccessKeyResponse,
    PakDeviceListResponse,
    PakDeviceResponse,
    PakTokenRequest,
    PakTokenResponse,
    UpdateActiveRequest,
    UpdateArchivedRequest,
    UpdatePakDeviceRequest,
)
from app.modules.pak.service import PakManagementService

router = APIRouter(prefix="/pak", tags=["pak"])


def _response(pak: PakDevice) -> PakDeviceResponse:
    return PakDeviceResponse(
        id=pak.id,
        code=pak.code,
        kind=pak.kind,
        oauth_client_id=pak.oauth_client_id,
        active=pak.is_active,
        last_seen_at=pak.last_seen_at,
        archived_at=pak.archived_at,
    )


def _service(request: Request) -> PakManagementService:
    return cast(PakManagementService, request.app.state.pak_management)


@router.get("", response_model=PakDeviceListResponse)
async def list_pak(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.READ))],
    request: Request,
    q: str | None = None,
    kind: PakDeviceKind | None = None,
    active: bool | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["code", "kind", "created_at", "last_seen_at", "archived_at"] = "code",
    order: Literal["asc", "desc"] = "asc",
) -> PakDeviceListResponse:
    paks, total = await _service(request).list(
        q=q,
        kind=kind,
        active=active,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return PakDeviceListResponse(
        items=[_response(pak) for pak in paks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/token", response_model=PakTokenResponse,)
async def issue_token(
    payload: PakTokenRequest,
    request: Request,
) -> PakTokenResponse:
    token = await _service(request).issue_machine_access_token(
        client_id=payload.client_id,
        access_key=payload.access_key.get_secret_value(),
    )

    return PakTokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        scope=" ".join(token.scopes),
    )


@router.get("/{pak_id}", response_model=PakDeviceResponse)
async def get_pak(
    pak_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.READ))],
    request: Request,
) -> PakDeviceResponse:
    pak = await _service(request).get(pak_id)

    if pak is None:
        raise PakNotFoundError

    return _response(pak)


@router.post("", response_model=CreatePakDeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_pak(
    payload: CreatePakDeviceRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.CREATE))],
    request: Request,
) -> CreatePakDeviceResponse:
    pak, access_key = await _service(request).create(
        actor=principal, code=payload.code, kind=payload.kind, active=payload.active
    )

    return CreatePakDeviceResponse(device=_response(pak), access_key=access_key)


@router.get("/{pak_id}/access-key", response_model=PakAccessKeyResponse)
async def get_access_key(
    pak_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(PakPermission.READ_ACCESS_KEY))
    ],
    request: Request,
) -> PakAccessKeyResponse:
    access_key = await _service(request).get_access_key(actor=principal, pak_id=pak_id)

    return PakAccessKeyResponse(access_key=access_key)


@router.post("/{pak_id}/access-key/rotate", response_model=PakAccessKeyResponse)
async def rotate_access_key(
    pak_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(PakPermission.ROTATE_ACCESS_KEY))
    ],
    request: Request,
) -> PakAccessKeyResponse:
    access_key = await _service(request).rotate_access_key(actor=principal, pak_id=pak_id)

    return PakAccessKeyResponse(access_key=access_key)


@router.patch("/{pak_id}", response_model=PakDeviceResponse)
async def update_pak(
    pak_id: UUID,
    payload: UpdatePakDeviceRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.UPDATE))],
    request: Request,
) -> PakDeviceResponse:
    return _response(
        await _service(request).update(
            actor=principal, pak_id=pak_id, code=payload.code, kind=payload.kind
        )
    )


@router.put("/{pak_id}/active", response_model=PakDeviceResponse)
async def update_active(
    pak_id: UUID,
    payload: UpdateActiveRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(PakPermission.SET_ACTIVE))
    ],
    request: Request,
) -> PakDeviceResponse:
    return _response(
        await _service(request).set_active(actor=principal, pak_id=pak_id, active=payload.active)
    )


@router.put("/{pak_id}/archived", response_model=PakDeviceResponse)
async def update_archived(
    pak_id: UUID,
    payload: UpdateArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.ARCHIVE))],
    request: Request,
) -> PakDeviceResponse:
    return _response(
        await _service(request).set_archived(
            actor=principal, pak_id=pak_id, archived=payload.archived
        )
    )


@router.delete("/{pak_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pak(
    pak_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.DELETE))],
    request: Request,
) -> None:
    await _service(request).delete(actor=principal, pak_id=pak_id)
