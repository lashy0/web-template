from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.domains.quality.checks.router import router as checks_router
from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission

from .exceptions import PakNotFoundError
from .model import PakDevice, PakDeviceKind
from .permissions import PakPermission
from .schemas import (
    CreatePakDeviceRequest,
    CreatePakDeviceResponse,
    PakAccessKeyResponse,
    PakDeviceListResponse,
    PakDeviceResponse,
    PakStatus,
    UpdateActiveRequest,
    UpdateArchivedRequest,
    UpdatePakDeviceRequest,
)
from .wiring import (
    OAuthClientDep,
    SettingsDep,
    VerificationHistoryFactoryDep,
    create_pak_command,
    create_queries,
    delete_pak_command,
    get_access_key_command,
    rotate_access_key_command,
    set_active_command,
    set_archived_command,
    update_pak_command,
)

router = APIRouter(prefix="/pak", tags=["pak"])
router.include_router(checks_router)


def _response(pak: PakDevice) -> PakDeviceResponse:
    return PakDeviceResponse(
        id=pak.id,
        code=pak.code,
        kind=pak.kind,
        oauth_client_id=pak.oauth_client_id,
        status=PakStatus.ACTIVE if pak.is_active else PakStatus.INACTIVE,
        last_seen_at=pak.last_seen_at,
        archived_at=pak.archived_at,
    )


@router.get("", response_model=PakDeviceListResponse)
async def list_pak(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.READ))],
    session_factory: SessionFactoryDep,
    q: str | None = None,
    kind: PakDeviceKind | None = None,
    status: PakStatus | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["code", "kind", "created_at", "last_seen_at", "archived_at"] = "code",
    order: Literal["asc", "desc"] = "asc",
) -> PakDeviceListResponse:
    paks, total = await create_queries(session_factory).list(
        q=q,
        kind=kind,
        active=None if status is None else status is PakStatus.ACTIVE,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    return PakDeviceListResponse(
        items=[_response(pak) for pak in paks], total=total, page=page, page_size=page_size
    )


@router.get("/{pak_id}", response_model=PakDeviceResponse)
async def get_pak(
    pak_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.READ))],
    session_factory: SessionFactoryDep,
) -> PakDeviceResponse:
    pak = await create_queries(session_factory).get(pak_id)
    if pak is None:
        raise PakNotFoundError
    return _response(pak)


@router.post("", response_model=CreatePakDeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_pak(
    payload: CreatePakDeviceRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.CREATE))],
    session_factory: SessionFactoryDep,
    oauth: OAuthClientDep,
    settings: SettingsDep,
) -> CreatePakDeviceResponse:
    pak, access_key = await create_pak_command(session_factory, oauth, settings).execute(
        actor=principal,
        code=payload.code,
        kind=payload.kind,
        active=payload.active,
    )
    return CreatePakDeviceResponse(device=_response(pak), access_key=access_key)


@router.get("/{pak_id}/access-key", response_model=PakAccessKeyResponse)
async def get_access_key(
    pak_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(PakPermission.READ_ACCESS_KEY))
    ],
    session_factory: SessionFactoryDep,
    settings: SettingsDep,
) -> PakAccessKeyResponse:
    access_key = await get_access_key_command(session_factory, settings).execute(
        actor=principal, pak_id=pak_id
    )
    return PakAccessKeyResponse(access_key=access_key)


@router.post("/{pak_id}/access-key/rotate", response_model=PakAccessKeyResponse)
async def rotate_access_key(
    pak_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(PakPermission.ROTATE_ACCESS_KEY))
    ],
    session_factory: SessionFactoryDep,
    oauth: OAuthClientDep,
    settings: SettingsDep,
) -> PakAccessKeyResponse:
    access_key = await rotate_access_key_command(session_factory, oauth, settings).execute(
        actor=principal, pak_id=pak_id
    )
    return PakAccessKeyResponse(access_key=access_key)


@router.patch("/{pak_id}", response_model=PakDeviceResponse)
async def update_pak(
    pak_id: UUID,
    payload: UpdatePakDeviceRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.UPDATE))],
    session_factory: SessionFactoryDep,
) -> PakDeviceResponse:
    pak = await update_pak_command(session_factory).execute(
        actor=principal, pak_id=pak_id, code=payload.code, kind=payload.kind
    )
    return _response(pak)


@router.put("/{pak_id}/active", response_model=PakDeviceResponse)
async def update_active(
    pak_id: UUID,
    payload: UpdateActiveRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(PakPermission.SET_ACTIVE))
    ],
    session_factory: SessionFactoryDep,
) -> PakDeviceResponse:
    pak = await set_active_command(session_factory).execute(
        actor=principal, pak_id=pak_id, active=payload.active
    )
    return _response(pak)


@router.put("/{pak_id}/archived", response_model=PakDeviceResponse)
async def update_archived(
    pak_id: UUID,
    payload: UpdateArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.ARCHIVE))],
    session_factory: SessionFactoryDep,
) -> PakDeviceResponse:
    pak = await set_archived_command(session_factory).execute(
        actor=principal, pak_id=pak_id, archived=payload.archived
    )
    return _response(pak)


@router.delete("/{pak_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pak(
    pak_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.DELETE))],
    session_factory: SessionFactoryDep,
    oauth: OAuthClientDep,
    verification_history: VerificationHistoryFactoryDep,
    settings: SettingsDep,
) -> None:
    await delete_pak_command(session_factory, oauth, verification_history, settings).execute(
        actor=principal, pak_id=pak_id
    )
