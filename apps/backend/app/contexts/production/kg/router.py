"""Compatibility-preserving HTTP adapter for migrated prefix/version operations."""

from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.audit.writer import TransactionalAuditWriter
from app.modules.kg.permissions import KgPermission
from app.shared.uow import transaction

from .commands import (
    CreatePrefix,
    CreateVersion,
    DeletePrefix,
    DeleteVersion,
    SetPrefixArchived,
    SetVersionArchived,
    UpdatePrefix,
    UpdateVersion,
)
from .model import KgDevEuiPrefix, KgVersion
from .queries import KgQueries
from .repository import KgRepository
from .schemas import (
    CreateKgDevEuiPrefixRequest,
    CreateKgVersionRequest,
    DevEuiPrefix,
    KgDevEuiPrefixListResponse,
    KgDevEuiPrefixResponse,
    KgVersionListResponse,
    KgVersionResponse,
    UpdateKgDevEuiPrefixArchivedRequest,
    UpdateKgDevEuiPrefixRequest,
    UpdateKgVersionArchivedRequest,
    UpdateKgVersionRequest,
)

prefix_router = APIRouter()
version_router = APIRouter()
router = APIRouter()
router.include_router(prefix_router, prefix="/kg", tags=["kg"])
router.include_router(version_router, prefix="/kg", tags=["kg"])


def _factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


def _prefix_response(item: KgDevEuiPrefix, batch_count: int) -> KgDevEuiPrefixResponse:
    return KgDevEuiPrefixResponse(
        prefix=item.prefix,
        short_code=item.short_code,
        name=item.name,
        batch_count=batch_count,
        created_at=item.created_at,
        archived_at=item.archived_at,
    )


def _version_response(item: KgVersion, batch_count: int) -> KgVersionResponse:
    return KgVersionResponse(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        batch_count=batch_count,
        created_at=item.created_at,
        updated_at=item.updated_at,
        archived_at=item.archived_at,
    )


@prefix_router.get("/dev-eui-prefixes", response_model=KgDevEuiPrefixListResponse)
async def list_dev_eui_prefixes(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_READ))],
    request: Request,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["prefix", "name", "short_code", "created_at", "archived_at"] = "prefix",
    order: Literal["asc", "desc"] = "asc",
) -> KgDevEuiPrefixListResponse:
    async with _factory(request)() as session:
        items, total = await KgQueries(KgRepository(session)).list_prefixes(
            q=q, archived=archived, page=page, page_size=page_size, sort=sort, order=order
        )
    return KgDevEuiPrefixListResponse(
        items=[_prefix_response(item, count) for item, count in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@prefix_router.post(
    "/dev-eui-prefixes", response_model=KgDevEuiPrefixResponse, status_code=status.HTTP_201_CREATED
)
async def create_dev_eui_prefix(
    payload: CreateKgDevEuiPrefixRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_CREATE))
    ],
    request: Request,
) -> KgDevEuiPrefixResponse:
    async with transaction(_factory(request)) as session:
        repository = KgRepository(session)
        item = await CreatePrefix(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, **payload.model_dump())
        count = await repository.count_batches_for_prefix(item.prefix)
    return _prefix_response(item, count)


@prefix_router.patch("/dev-eui-prefixes/{prefix}", response_model=KgDevEuiPrefixResponse)
async def update_dev_eui_prefix(
    prefix: DevEuiPrefix,
    payload: UpdateKgDevEuiPrefixRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_UPDATE))
    ],
    request: Request,
) -> KgDevEuiPrefixResponse:
    async with transaction(_factory(request)) as session:
        repository = KgRepository(session)
        item = await UpdatePrefix(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, prefix=prefix, updates=payload.model_dump(exclude_unset=True))
        count = await repository.count_batches_for_prefix(item.prefix)
    return _prefix_response(item, count)


@prefix_router.put("/dev-eui-prefixes/{prefix}/archived", response_model=KgDevEuiPrefixResponse)
async def update_dev_eui_prefix_archived(
    prefix: DevEuiPrefix,
    payload: UpdateKgDevEuiPrefixArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_ARCHIVE))
    ],
    request: Request,
) -> KgDevEuiPrefixResponse:
    async with transaction(_factory(request)) as session:
        repository = KgRepository(session)
        item = await SetPrefixArchived(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, prefix=prefix, archived=payload.archived)
        count = await repository.count_batches_for_prefix(item.prefix)
    return _prefix_response(item, count)


@prefix_router.delete("/dev-eui-prefixes/{prefix}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dev_eui_prefix(
    prefix: DevEuiPrefix,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_DELETE))
    ],
    request: Request,
) -> None:
    async with transaction(_factory(request)) as session:
        await DeletePrefix(
            KgRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, prefix=prefix)


@version_router.get("/versions", response_model=KgVersionListResponse)
async def list_kg_versions(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_READ))],
    request: Request,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: Literal[
        "code", "name", "description", "created_at", "updated_at", "archived_at"
    ] = "code",
    sort_order: Literal["asc", "desc"] = "asc",
) -> KgVersionListResponse:
    async with _factory(request)() as session:
        items, total = await KgQueries(KgRepository(session)).list_versions(
            q=q,
            archived=archived,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    return KgVersionListResponse(
        items=[_version_response(item, count) for item, count in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@version_router.post(
    "/versions", response_model=KgVersionResponse, status_code=status.HTTP_201_CREATED
)
async def create_kg_version(
    payload: CreateKgVersionRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_CREATE))
    ],
    request: Request,
) -> KgVersionResponse:
    async with transaction(_factory(request)) as session:
        repository = KgRepository(session)
        item = await CreateVersion(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, **payload.model_dump())
        count = await repository.count_batches_for_version(item.id)
    return _version_response(item, count)


@version_router.patch("/versions/{version_id}", response_model=KgVersionResponse)
async def update_kg_version(
    version_id: UUID,
    payload: UpdateKgVersionRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_UPDATE))
    ],
    request: Request,
) -> KgVersionResponse:
    async with transaction(_factory(request)) as session:
        repository = KgRepository(session)
        item = await UpdateVersion(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(
            actor=principal, version_id=version_id, updates=payload.model_dump(exclude_unset=True)
        )
        count = await repository.count_batches_for_version(item.id)
    return _version_response(item, count)


@version_router.put("/versions/{version_id}/archived", response_model=KgVersionResponse)
async def update_kg_version_archived(
    version_id: UUID,
    payload: UpdateKgVersionArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_ARCHIVE))
    ],
    request: Request,
) -> KgVersionResponse:
    async with transaction(_factory(request)) as session:
        repository = KgRepository(session)
        item = await SetVersionArchived(
            repository, TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, version_id=version_id, archived=payload.archived)
        count = await repository.count_batches_for_version(item.id)
    return _version_response(item, count)


@version_router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kg_version(
    version_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_DELETE))
    ],
    request: Request,
) -> None:
    async with transaction(_factory(request)) as session:
        await DeleteVersion(
            KgRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(actor=principal, version_id=version_id)
