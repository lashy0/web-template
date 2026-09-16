"""Compatibility-preserving HTTP adapter for migrated prefix/version operations."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission
from app.shared.uow import transaction

from .exceptions import KgNotFoundError
from .model import KgDevEuiPrefix, KgUnit, KgVersion
from .permissions import KgPermission
from .schemas import (
    CreateKgDevEuiPrefixRequest,
    CreateKgVersionRequest,
    DevEui,
    DevEuiPrefix,
    KgBatchListItemResponse,
    KgBatchListResponse,
    KgBatchSummaryResponse,
    KgCurrentState,
    KgDevEuiPrefixListResponse,
    KgDevEuiPrefixResponse,
    KgListResponse,
    KgResponse,
    KgVersionListResponse,
    KgVersionResponse,
    UpdateKgDevEuiPrefixArchivedRequest,
    UpdateKgDevEuiPrefixRequest,
    UpdateKgVersionArchivedRequest,
    UpdateKgVersionRequest,
)
from .wiring import (
    ProjectionFactoryDep,
    create_prefix_command,
    create_queries,
    create_repository,
    create_version_command,
    delete_prefix_command,
    delete_version_command,
    set_prefix_archived_command,
    set_version_archived_command,
    update_prefix_command,
    update_version_command,
)

prefix_router = APIRouter()
version_router = APIRouter()
router = APIRouter()
router.include_router(prefix_router, prefix="/kg", tags=["kg"])
router.include_router(version_router, prefix="/kg", tags=["kg"])


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


def _kg_response(kg: KgUnit, *, current_state: KgCurrentState) -> KgResponse:
    return KgResponse(
        dev_eui=kg.dev_eui,
        short_id=kg.short_id,
        batch_id=kg.batch_id,
        batch=KgBatchSummaryResponse(id=kg.batch.id, name=kg.batch.name),
        state=kg.state,
        current_state=current_state,
        created_at=kg.created_at,
        updated_at=kg.updated_at,
    )


@router.get("/kg/batch/{batch_id}", response_model=KgBatchListResponse)
async def list_kg_by_batch(
    batch_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.READ))],
    session_factory: SessionFactoryDep,
    projection_factory: ProjectionFactoryDep,
    q: str | None = None,
    current_state: KgCurrentState | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> KgBatchListResponse:
    async with session_factory() as session:
        items, total = await create_queries(session, projection_factory).list_batch_items(
            batch_id, page=page, page_size=page_size, q=q, current_state=current_state
        )
    return KgBatchListResponse(
        items=[
            KgBatchListItemResponse(
                dev_eui=item.dev_eui,
                current_state=item.current_state,
                firmware_version=item.firmware_version,
                last_verification_at=item.last_verification_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/kg", response_model=KgListResponse)
async def list_kg(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.READ))],
    session_factory: SessionFactoryDep,
    projection_factory: ProjectionFactoryDep,
    q: str | None = None,
    batch_id: UUID | None = None,
    current_state: KgCurrentState | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "dev_eui", "batch_id", "current_state", "created_at", "updated_at"
    ] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> KgListResponse:
    async with session_factory() as session:
        items, total = await create_queries(session, projection_factory).list(
            q=q,
            batch_id=batch_id,
            current_state=current_state,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )
    return KgListResponse(
        items=[_kg_response(item.kg, current_state=item.current_state) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/kg/{dev_eui}", response_model=KgResponse)
async def get_kg(
    dev_eui: DevEui,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.READ))],
    session_factory: SessionFactoryDep,
    projection_factory: ProjectionFactoryDep,
) -> KgResponse:
    async with session_factory() as session:
        item = await create_queries(session, projection_factory).get_with_current_state(dev_eui)
    if item is None:
        raise KgNotFoundError
    return _kg_response(item.kg, current_state=item.current_state)


@prefix_router.get("/dev-eui-prefixes", response_model=KgDevEuiPrefixListResponse)
async def list_dev_eui_prefixes(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_READ))],
    session_factory: SessionFactoryDep,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["prefix", "name", "short_code", "created_at", "archived_at"] = "prefix",
    order: Literal["asc", "desc"] = "asc",
) -> KgDevEuiPrefixListResponse:
    async with session_factory() as session:
        items, total = await create_queries(session).list_prefixes(
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
    session_factory: SessionFactoryDep,
) -> KgDevEuiPrefixResponse:
    async with transaction(session_factory) as session:
        item = await create_prefix_command(session).execute(actor=principal, **payload.model_dump())
        count = await create_repository(session).count_batches_for_prefix(item.prefix)
    return _prefix_response(item, count)


@prefix_router.patch("/dev-eui-prefixes/{prefix}", response_model=KgDevEuiPrefixResponse)
async def update_dev_eui_prefix(
    prefix: DevEuiPrefix,
    payload: UpdateKgDevEuiPrefixRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_UPDATE))
    ],
    session_factory: SessionFactoryDep,
) -> KgDevEuiPrefixResponse:
    async with transaction(session_factory) as session:
        item = await update_prefix_command(session).execute(
            actor=principal, prefix=prefix, updates=payload.model_dump(exclude_unset=True)
        )
        count = await create_repository(session).count_batches_for_prefix(item.prefix)
    return _prefix_response(item, count)


@prefix_router.put("/dev-eui-prefixes/{prefix}/archived", response_model=KgDevEuiPrefixResponse)
async def update_dev_eui_prefix_archived(
    prefix: DevEuiPrefix,
    payload: UpdateKgDevEuiPrefixArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_ARCHIVE))
    ],
    session_factory: SessionFactoryDep,
) -> KgDevEuiPrefixResponse:
    async with transaction(session_factory) as session:
        item = await set_prefix_archived_command(session).execute(
            actor=principal, prefix=prefix, archived=payload.archived
        )
        count = await create_repository(session).count_batches_for_prefix(item.prefix)
    return _prefix_response(item, count)


@prefix_router.delete("/dev-eui-prefixes/{prefix}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dev_eui_prefix(
    prefix: DevEuiPrefix,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.PREFIX_DELETE))
    ],
    session_factory: SessionFactoryDep,
) -> None:
    async with transaction(session_factory) as session:
        await delete_prefix_command(session).execute(actor=principal, prefix=prefix)


@version_router.get("/versions", response_model=KgVersionListResponse)
async def list_kg_versions(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_READ))],
    session_factory: SessionFactoryDep,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: Literal[
        "code", "name", "description", "created_at", "updated_at", "archived_at"
    ] = "code",
    sort_order: Literal["asc", "desc"] = "asc",
) -> KgVersionListResponse:
    async with session_factory() as session:
        items, total = await create_queries(session).list_versions(
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
    session_factory: SessionFactoryDep,
) -> KgVersionResponse:
    async with transaction(session_factory) as session:
        item = await create_version_command(session).execute(
            actor=principal, **payload.model_dump()
        )
        count = await create_repository(session).count_batches_for_version(item.id)
    return _version_response(item, count)


@version_router.patch("/versions/{version_id}", response_model=KgVersionResponse)
async def update_kg_version(
    version_id: UUID,
    payload: UpdateKgVersionRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_UPDATE))
    ],
    session_factory: SessionFactoryDep,
) -> KgVersionResponse:
    async with transaction(session_factory) as session:
        item = await update_version_command(session).execute(
            actor=principal, version_id=version_id, updates=payload.model_dump(exclude_unset=True)
        )
        count = await create_repository(session).count_batches_for_version(item.id)
    return _version_response(item, count)


@version_router.put("/versions/{version_id}/archived", response_model=KgVersionResponse)
async def update_kg_version_archived(
    version_id: UUID,
    payload: UpdateKgVersionArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_ARCHIVE))
    ],
    session_factory: SessionFactoryDep,
) -> KgVersionResponse:
    async with transaction(session_factory) as session:
        item = await set_version_archived_command(session).execute(
            actor=principal, version_id=version_id, archived=payload.archived
        )
        count = await create_repository(session).count_batches_for_version(item.id)
    return _version_response(item, count)


@version_router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kg_version(
    version_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_DELETE))
    ],
    session_factory: SessionFactoryDep,
) -> None:
    async with transaction(session_factory) as session:
        await delete_version_command(session).execute(actor=principal, version_id=version_id)
