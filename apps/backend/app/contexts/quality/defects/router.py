from collections.abc import Mapping
from typing import Annotated, Literal, Protocol, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.defects.permissions import DefectPermission
from app.shared.security import CurrentPrincipal

from .exceptions import DefectGroupNotFoundError, DefectTypeNotFoundError
from .model import DefectGroup, DefectType
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


class DefectOperations(Protocol):
    async def get_group(self, group_id: UUID) -> DefectGroup | None: ...
    async def list_groups(
        self, **kwargs: object
    ) -> tuple[list[tuple[DefectGroup, int, int]], int]: ...
    async def create_group(
        self, *, actor: CurrentPrincipal, code: str, name: str, description: str | None
    ) -> DefectGroup: ...
    async def update_group(
        self, *, actor: CurrentPrincipal, group_id: UUID, updates: Mapping[str, object]
    ) -> DefectGroup: ...
    async def set_group_archived(
        self, *, actor: CurrentPrincipal, group_id: UUID, archived: bool
    ) -> DefectGroup: ...
    async def delete_group(self, *, actor: CurrentPrincipal, group_id: UUID) -> None: ...
    async def get_type(self, item_id: UUID) -> DefectType | None: ...
    async def list_types(self, **kwargs: object) -> tuple[list[DefectType], int]: ...
    async def create_type(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
        code: str,
        name: str,
        description: str,
        possible_cause: str | None,
        engineer_action: str | None,
    ) -> DefectType: ...
    async def update_type(
        self, *, actor: CurrentPrincipal, defect_type_id: UUID, updates: Mapping[str, object]
    ) -> DefectType: ...
    async def set_type_archived(
        self, *, actor: CurrentPrincipal, defect_type_id: UUID, archived: bool
    ) -> DefectType: ...
    async def delete_type(self, *, actor: CurrentPrincipal, defect_type_id: UUID) -> None: ...


def _operations(request: Request) -> DefectOperations:
    return cast(DefectOperations, request.app.state.defect_management)


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
    items, total = await _operations(request).list_groups(
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
    item = await _operations(request).get_group(group_id)
    if item is None:
        raise DefectGroupNotFoundError
    return _group_response(item)


@router.post("/groups", response_model=DefectGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: CreateDefectGroupRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.CREATE))],
    request: Request,
) -> DefectGroupResponse:
    return _group_response(
        await _operations(request).create_group(
            actor=actor, code=payload.code, name=payload.name, description=payload.description
        )
    )


@router.patch("/groups/{group_id}", response_model=DefectGroupResponse)
async def update_group(
    group_id: UUID,
    payload: UpdateDefectGroupRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.UPDATE))],
    request: Request,
) -> DefectGroupResponse:
    return _group_response(
        await _operations(request).update_group(
            actor=actor, group_id=group_id, updates=payload.model_dump(exclude_unset=True)
        )
    )


@router.put("/groups/{group_id}/archived", response_model=DefectGroupResponse)
async def set_group_archived(
    group_id: UUID,
    payload: UpdateDefectGroupArchivedRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.ARCHIVE))],
    request: Request,
) -> DefectGroupResponse:
    return _group_response(
        await _operations(request).set_group_archived(
            actor=actor, group_id=group_id, archived=payload.archived
        )
    )


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: UUID,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.DELETE))],
    request: Request,
) -> None:
    await _operations(request).delete_group(actor=actor, group_id=group_id)


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
    items, total = await _operations(request).list_types(
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
    item = await _operations(request).get_type(item_id)
    if item is None:
        raise DefectTypeNotFoundError
    return _type_response(item)


@router.post("/types", response_model=DefectTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_type(
    payload: CreateDefectTypeRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.CREATE))],
    request: Request,
) -> DefectTypeResponse:
    item = await _operations(request).create_type(actor=actor, **payload.model_dump())
    return _type_response(item)


@router.patch("/types/{item_id}", response_model=DefectTypeResponse)
async def update_type(
    item_id: UUID,
    payload: UpdateDefectTypeRequest,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.UPDATE))],
    request: Request,
) -> DefectTypeResponse:
    item = await _operations(request).update_type(
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
    item = await _operations(request).set_type_archived(
        actor=actor, defect_type_id=item_id, archived=payload.archived
    )
    return _type_response(item)


@router.delete("/types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_type(
    item_id: UUID,
    actor: Annotated[CurrentPrincipalDep, Depends(require_permission(DefectPermission.DELETE))],
    request: Request,
) -> None:
    await _operations(request).delete_type(actor=actor, defect_type_id=item_id)
