from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.defects.exceptions import (
    DefectGroupNotFoundError,
    DefectTypeNotFoundError,
)
from app.modules.defects.models import DefectGroup, DefectType
from app.modules.defects.permissions import DefectPermission
from app.modules.defects.schemas import (
    CreateDefectGroupRequest,
    CreateDefectTypeRequest,
    DefectGroupListResponse,
    DefectGroupResponse,
    DefectTypeListResponse,
    DefectTypeResponse,
    UpdateDefectGroupArchivedRequest,
    UpdateDefectGroupRequest,
    UpdateDefectTypeArchivedRequest,
    UpdateDefectTypeRequest,
)
from app.modules.defects.service import DefectManagementService


router = APIRouter(prefix="/defects", tags=["defects"])


def _service(request: Request) -> DefectManagementService:
    return cast(
        DefectManagementService,
        request.app.state.defect_management,
    )


def _group_response(group: DefectGroup) -> DefectGroupResponse:
    return DefectGroupResponse(
        id=group.id,
        code=group.code,
        name=group.name,
        description=group.description,
        archived_at=group.archived_at,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def _type_response(defect_type: DefectType) -> DefectTypeResponse:
    return DefectTypeResponse(
        id=defect_type.id,
        group_id=defect_type.group_id,
        code=defect_type.code,
        name=defect_type.name,
        description=defect_type.description,
        possible_cause=defect_type.possible_cause,
        engineer_action=defect_type.engineer_action,
        archived_at=defect_type.archived_at,
        created_at=defect_type.created_at,
        updated_at=defect_type.updated_at,
    )


@router.get("/groups", response_model=DefectGroupListResponse)
async def list_defect_groups(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.READ
            )
        ),
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
            _group_response(group)
            for group in groups
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
        Depends(
            require_permission(
                DefectPermission.READ
            )
        ),
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
        Depends(
            require_permission(
                DefectPermission.CREATE
            )
        ),
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
        Depends(
            require_permission(
                DefectPermission.UPDATE
            )
        ),
    ],
    request: Request,
) -> DefectGroupResponse:
    group = await _service(request).update_group(
        actor=principal,
        group_id=group_id,
        updates=payload.model_dump(
            exclude_unset=True
        ),
    )

    return _group_response(group)


@router.put("/groups/{group_id}/archived", response_model=DefectGroupResponse)
async def update_defect_group_archived(
    group_id: UUID,
    payload: UpdateDefectGroupArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.ARCHIVE
            )
        ),
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
        Depends(
            require_permission(
                DefectPermission.DELETE
            )
        ),
    ],
    request: Request,
) -> None:
    await _service(request).delete_group(
        actor=principal,
        group_id=group_id,
    )


@router.get("/types", response_model=DefectTypeListResponse)
async def list_defect_types(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.READ
            )
        ),
    ],
    request: Request,
    q: str | None = None,
    group_id: UUID | None = None,
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
) -> DefectTypeListResponse:
    defect_types, total = await _service(request).list_types(
        q=q,
        group_id=group_id,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return DefectTypeListResponse(
        items=[
            _type_response(defect_type)
            for defect_type in defect_types
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/types/{defect_type_id}", response_model=DefectTypeResponse)
async def get_defect_type(
    defect_type_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.READ
            )
        ),
    ],
    request: Request,
) -> DefectTypeResponse:
    defect_type = await _service(request).get_type(
        defect_type_id
    )

    if defect_type is None:
        raise DefectTypeNotFoundError

    return _type_response(defect_type)


@router.post(
    "/types",
    response_model=DefectTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_defect_type(
    payload: CreateDefectTypeRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.CREATE
            )
        ),
    ],
    request: Request,
) -> DefectTypeResponse:
    defect_type = await _service(request).create_type(
        actor=principal,
        group_id=payload.group_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        possible_cause=payload.possible_cause,
        engineer_action=payload.engineer_action,
    )

    return _type_response(defect_type)


@router.patch("/types/{defect_type_id}", response_model=DefectTypeResponse)
async def update_defect_type(
    defect_type_id: UUID,
    payload: UpdateDefectTypeRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.UPDATE
            )
        ),
    ],
    request: Request,
) -> DefectTypeResponse:
    defect_type = await _service(request).update_type(
        actor=principal,
        defect_type_id=defect_type_id,
        updates=payload.model_dump(
            exclude_unset=True
        ),
    )

    return _type_response(defect_type)


@router.put("/types/{defect_type_id}/archived", response_model=DefectTypeResponse)
async def update_defect_type_archived(
    defect_type_id: UUID,
    payload: UpdateDefectTypeArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.ARCHIVE
            )
        ),
    ],
    request: Request,
) -> DefectTypeResponse:
    defect_type = await _service(request).set_type_archived(
        actor=principal,
        defect_type_id=defect_type_id,
        archived=payload.archived,
    )

    return _type_response(defect_type)


@router.delete("/types/{defect_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_defect_type(
    defect_type_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                DefectPermission.DELETE
            )
        ),
    ],
    request: Request,
) -> None:
    await _service(request).delete_type(
        actor=principal,
        defect_type_id=defect_type_id,
    )
