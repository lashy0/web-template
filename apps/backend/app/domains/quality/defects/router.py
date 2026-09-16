from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission

from .commands import (
    CreateDefectGroup,
    CreateDefectType,
    DeleteDefectGroup,
    DeleteDefectType,
    SetDefectGroupArchived,
    SetDefectTypeArchived,
    UpdateDefectGroup,
    UpdateDefectType,
)
from .exceptions import DefectGroupNotFoundError, DefectTypeNotFoundError
from .model import DefectGroup, DefectType
from .permissions import DefectPermission
from .queries import DefectQueries
from .repository import DefectGroupRepository, DefectTypeRepository
from .schemas import (
    CreateDefectGroupRequest,
    CreateDefectTypeRequest,
    DefectGroupListItemResponse,
    DefectGroupListResponse,
    DefectGroupResponse,
    DefectGroupSummaryResponse,
    DefectTypeListResponse,
    DefectTypeResponse,
    UpdateDefectGroupArchivedRequest,
    UpdateDefectGroupRequest,
    UpdateDefectTypeArchivedRequest,
    UpdateDefectTypeRequest,
)

router = APIRouter(prefix="/defects", tags=["defects"])


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


@asynccontextmanager
async def _transaction(request: Request) -> AsyncIterator[AsyncSession]:
    async with _session_factory(request)() as session, session.begin():
        yield session


def _queries(session: AsyncSession) -> DefectQueries:
    return DefectQueries(DefectGroupRepository(session), DefectTypeRepository(session))


def _group_response(
    item: DefectGroup, *, active_types_count: int | None = None, types_count: int | None = None
) -> DefectGroupResponse:
    return DefectGroupResponse(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        archived_at=item.archived_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        active_types_count=sum(member.archived_at is None for member in item.types)
        if active_types_count is None
        else active_types_count,
        types_count=len(item.types) if types_count is None else types_count,
    )


def _type_response(item: DefectType) -> DefectTypeResponse:
    return DefectTypeResponse(
        id=item.id,
        group_id=item.group_id,
        group=DefectGroupSummaryResponse(
            id=item.group.id,
            code=item.group.code,
            name=item.group.name,
            archived_at=item.group.archived_at,
        ),
        code=item.code,
        name=item.name,
        description=item.description,
        possible_cause=item.possible_cause,
        engineer_action=item.engineer_action,
        archived_at=item.archived_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/groups", response_model=DefectGroupListResponse)
async def list_groups(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.READ))],
    request: Request,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["code", "name", "created_at", "updated_at", "archived_at"] = "code",
    order: Literal["asc", "desc"] = "asc",
) -> DefectGroupListResponse:
    async with _session_factory(request)() as session:
        items, total = await _queries(session).list_groups(
            q=q, archived=archived, page=page, page_size=page_size, sort=sort, order=order
        )
    return DefectGroupListResponse(
        items=[
            DefectGroupListItemResponse(
                **_group_response(item, active_types_count=active, types_count=count).model_dump()
            )
            for item, active, count in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/groups/{group_id}", response_model=DefectGroupResponse)
async def get_group(
    group_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.READ))],
    request: Request,
) -> DefectGroupResponse:
    async with _session_factory(request)() as session:
        item = await _queries(session).get_group(group_id)
    if item is None:
        raise DefectGroupNotFoundError
    return _group_response(item)


@router.post("/groups", response_model=DefectGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: CreateDefectGroupRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.CREATE))],
    request: Request,
) -> DefectGroupResponse:
    async with _transaction(request) as session:
        item = await CreateDefectGroup(
            DefectGroupRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(
            actor=actor, code=payload.code, name=payload.name, description=payload.description
        )
    return _group_response(item)


@router.patch("/groups/{group_id}", response_model=DefectGroupResponse)
async def update_group(
    group_id: UUID,
    payload: UpdateDefectGroupRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.UPDATE))],
    request: Request,
) -> DefectGroupResponse:
    async with _transaction(request) as session:
        item = await UpdateDefectGroup(
            DefectGroupRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(actor=actor, group_id=group_id, updates=payload.model_dump(exclude_unset=True))
    return _group_response(item)


@router.put("/groups/{group_id}/archived", response_model=DefectGroupResponse)
async def set_group_archived(
    group_id: UUID,
    payload: UpdateDefectGroupArchivedRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.ARCHIVE))],
    request: Request,
) -> DefectGroupResponse:
    async with _transaction(request) as session:
        item = await SetDefectGroupArchived(
            DefectGroupRepository(session),
            DefectTypeRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(actor=actor, group_id=group_id, archived=payload.archived)
    return _group_response(item)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: UUID,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.DELETE))],
    request: Request,
) -> None:
    async with _transaction(request) as session:
        await DeleteDefectGroup(
            DefectGroupRepository(session),
            DefectTypeRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(actor=actor, group_id=group_id)


@router.get("/types", response_model=DefectTypeListResponse)
async def list_types(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.READ))],
    request: Request,
    q: str | None = None,
    group_id: UUID | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["code", "name", "created_at", "updated_at", "archived_at"] = "code",
    order: Literal["asc", "desc"] = "asc",
) -> DefectTypeListResponse:
    async with _session_factory(request)() as session:
        items, total = await _queries(session).list_types(
            q=q,
            group_id=group_id,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )
    return DefectTypeListResponse(
        items=[_type_response(item) for item in items], total=total, page=page, page_size=page_size
    )


@router.get("/types/{item_id}", response_model=DefectTypeResponse)
async def get_type(
    item_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.READ))],
    request: Request,
) -> DefectTypeResponse:
    async with _session_factory(request)() as session:
        item = await _queries(session).get_type(item_id)
    if item is None:
        raise DefectTypeNotFoundError
    return _type_response(item)


@router.post("/types", response_model=DefectTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_type(
    payload: CreateDefectTypeRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.CREATE))],
    request: Request,
) -> DefectTypeResponse:
    async with _transaction(request) as session:
        item = await CreateDefectType(
            DefectGroupRepository(session),
            DefectTypeRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(actor=actor, **payload.model_dump())
    return _type_response(item)


@router.patch("/types/{item_id}", response_model=DefectTypeResponse)
async def update_type(
    item_id: UUID,
    payload: UpdateDefectTypeRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.UPDATE))],
    request: Request,
) -> DefectTypeResponse:
    async with _transaction(request) as session:
        item = await UpdateDefectType(
            DefectTypeRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(
            actor=actor, defect_type_id=item_id, updates=payload.model_dump(exclude_unset=True)
        )
    return _type_response(item)


@router.put("/types/{item_id}/archived", response_model=DefectTypeResponse)
async def set_type_archived(
    item_id: UUID,
    payload: UpdateDefectTypeArchivedRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.ARCHIVE))],
    request: Request,
) -> DefectTypeResponse:
    async with _transaction(request) as session:
        item = await SetDefectTypeArchived(
            DefectGroupRepository(session),
            DefectTypeRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(actor=actor, defect_type_id=item_id, archived=payload.archived)
    return _type_response(item)


@router.delete("/types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_type(
    item_id: UUID,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.DELETE))],
    request: Request,
) -> None:
    async with _transaction(request) as session:
        await DeleteDefectType(
            DefectTypeRepository(session), TransactionalAuditWriter.from_session(session)
        ).execute(actor=actor, defect_type_id=item_id)
