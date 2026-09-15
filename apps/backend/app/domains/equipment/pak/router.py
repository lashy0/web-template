from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.domains.quality.tests.router import router as tests_router
from app.domains.quality.verification.adapters import QualityPakVerificationHistoryAdapter
from app.infrastructure.hydra.pak import HydraPakOAuthClientAdapter

from .commands import (
    CreatePak,
    DeletePak,
    GetPakAccessKey,
    RotatePakAccessKey,
    SetPakActive,
    SetPakArchived,
    UpdatePak,
)
from .exceptions import PakNotFoundError
from .model import PakDevice, PakDeviceKind
from .permissions import PakPermission
from .queries import PakQueries
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

router = APIRouter(prefix="/pak", tags=["pak"])
router.include_router(tests_router)


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


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


def _oauth(request: Request) -> HydraPakOAuthClientAdapter:
    return HydraPakOAuthClientAdapter(request.app.state.hydra_client_manager)


@router.get("", response_model=PakDeviceListResponse)
async def list_pak(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.READ))],
    request: Request,
    q: str | None = None,
    kind: PakDeviceKind | None = None,
    status: PakStatus | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["code", "kind", "created_at", "last_seen_at", "archived_at"] = "code",
    order: Literal["asc", "desc"] = "asc",
) -> PakDeviceListResponse:
    paks, total = await PakQueries(_session_factory(request)).list(
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
    request: Request,
) -> PakDeviceResponse:
    pak = await PakQueries(_session_factory(request)).get(pak_id)
    if pak is None:
        raise PakNotFoundError
    return _response(pak)


@router.post("", response_model=CreatePakDeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_pak(
    payload: CreatePakDeviceRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.CREATE))],
    request: Request,
) -> CreatePakDeviceResponse:
    pak, access_key = await CreatePak(
        _session_factory(request),
        _oauth(request),
        request.app.state.settings.PAK_ACCESS_KEY_ENCRYPTION_KEY,
    ).execute(
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
    request: Request,
) -> PakAccessKeyResponse:
    access_key = await GetPakAccessKey(
        _session_factory(request), request.app.state.settings.PAK_ACCESS_KEY_ENCRYPTION_KEY
    ).execute(actor=principal, pak_id=pak_id)
    return PakAccessKeyResponse(access_key=access_key)


@router.post("/{pak_id}/access-key/rotate", response_model=PakAccessKeyResponse)
async def rotate_access_key(
    pak_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(PakPermission.ROTATE_ACCESS_KEY))
    ],
    request: Request,
) -> PakAccessKeyResponse:
    access_key = await RotatePakAccessKey(
        _session_factory(request),
        _oauth(request),
        request.app.state.settings.PAK_ACCESS_KEY_ENCRYPTION_KEY,
    ).execute(actor=principal, pak_id=pak_id)
    return PakAccessKeyResponse(access_key=access_key)


@router.patch("/{pak_id}", response_model=PakDeviceResponse)
async def update_pak(
    pak_id: UUID,
    payload: UpdatePakDeviceRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.UPDATE))],
    request: Request,
) -> PakDeviceResponse:
    pak = await UpdatePak(_session_factory(request)).execute(
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
    request: Request,
) -> PakDeviceResponse:
    pak = await SetPakActive(_session_factory(request)).execute(
        actor=principal, pak_id=pak_id, active=payload.active
    )
    return _response(pak)


@router.put("/{pak_id}/archived", response_model=PakDeviceResponse)
async def update_archived(
    pak_id: UUID,
    payload: UpdateArchivedRequest,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.ARCHIVE))],
    request: Request,
) -> PakDeviceResponse:
    pak = await SetPakArchived(_session_factory(request)).execute(
        actor=principal, pak_id=pak_id, archived=payload.archived
    )
    return _response(pak)


@router.delete("/{pak_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pak(
    pak_id: UUID,
    principal: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.DELETE))],
    request: Request,
) -> None:
    await DeletePak(
        _session_factory(request),
        _oauth(request),
        QualityPakVerificationHistoryAdapter,
        request.app.state.settings.PAK_ACCESS_KEY_ENCRYPTION_KEY,
    ).execute(actor=principal, pak_id=pak_id)
