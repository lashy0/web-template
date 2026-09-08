from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..exceptions import DefectGroupNotFoundError
from ..permissions import DefectPermission
from ..schemas import (
    CreateDefectGroupRequest,
    DefectGroupListItemResponse,
    DefectGroupListResponse,
    DefectGroupResponse,
    UpdateDefectGroupArchivedRequest,
    UpdateDefectGroupRequest,
)
from .common import _group_response, _service

router = APIRouter()


@router.get("/groups", response_model=DefectGroupListResponse)
async def list_defect_groups(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.READ)),
    ],
    request: Request,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "code",
        "name",
        "created_at",
        "updated_at",
        "archived_at",
    ] = "code",
    order: Literal["asc", "desc"] = "asc",
) -> DefectGroupListResponse:
    groups, total = await _service(request).list_groups(
        q=q,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return DefectGroupListResponse(
        items=[
            DefectGroupListItemResponse(
                **_group_response(
                    group, active_types_count=active_types_count, types_count=types_count
                ).model_dump(),
            )
            for group, active_types_count, types_count in groups
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/groups/{group_id}", response_model=DefectGroupResponse)
async def get_defect_group(
    group_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.READ)),
    ],
    request: Request,
) -> DefectGroupResponse:
    group = await _service(request).get_group(group_id)

    if group is None:
        raise DefectGroupNotFoundError

    return _group_response(group)


@router.post(
    "/groups",
    response_model=DefectGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_defect_group(
    payload: CreateDefectGroupRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.CREATE)),
    ],
    request: Request,
) -> DefectGroupResponse:
    group = await _service(request).create_group(
        actor=principal,
        code=payload.code,
        name=payload.name,
        description=payload.description,
    )

    return _group_response(group)


@router.patch("/groups/{group_id}", response_model=DefectGroupResponse)
async def update_defect_group(
    group_id: UUID,
    payload: UpdateDefectGroupRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.UPDATE)),
    ],
    request: Request,
) -> DefectGroupResponse:
    group = await _service(request).update_group(
        actor=principal,
        group_id=group_id,
        updates=payload.model_dump(exclude_unset=True),
    )

    return _group_response(group)


@router.put("/groups/{group_id}/archived", response_model=DefectGroupResponse)
async def update_defect_group_archived(
    group_id: UUID,
    payload: UpdateDefectGroupArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.ARCHIVE)),
    ],
    request: Request,
) -> DefectGroupResponse:
    group = await _service(request).set_group_archived(
        actor=principal,
        group_id=group_id,
        archived=payload.archived,
    )

    return _group_response(group)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_defect_group(
    group_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.DELETE)),
    ],
    request: Request,
) -> None:
    await _service(request).delete_group(
        actor=principal,
        group_id=group_id,
    )
