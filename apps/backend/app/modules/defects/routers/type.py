from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..exceptions import DefectTypeNotFoundError
from ..permissions import DefectPermission
from ..schemas import (
    CreateDefectTypeRequest,
    DefectTypeListResponse,
    DefectTypeResponse,
    UpdateDefectTypeArchivedRequest,
    UpdateDefectTypeRequest,
)
from .common import _service, _type_response

router = APIRouter()


@router.get("/types", response_model=DefectTypeListResponse)
async def list_defect_types(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.READ)),
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
        items=[_type_response(defect_type) for defect_type in defect_types],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/types/{defect_type_id}", response_model=DefectTypeResponse)
async def get_defect_type(
    defect_type_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.READ)),
    ],
    request: Request,
) -> DefectTypeResponse:
    defect_type = await _service(request).get_type(defect_type_id)

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
        Depends(require_permission(DefectPermission.CREATE)),
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
        Depends(require_permission(DefectPermission.UPDATE)),
    ],
    request: Request,
) -> DefectTypeResponse:
    defect_type = await _service(request).update_type(
        actor=principal,
        defect_type_id=defect_type_id,
        updates=payload.model_dump(exclude_unset=True),
    )

    return _type_response(defect_type)


@router.put("/types/{defect_type_id}/archived", response_model=DefectTypeResponse)
async def update_defect_type_archived(
    defect_type_id: UUID,
    payload: UpdateDefectTypeArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(DefectPermission.ARCHIVE)),
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
        Depends(require_permission(DefectPermission.DELETE)),
    ],
    request: Request,
) -> None:
    await _service(request).delete_type(
        actor=principal,
        defect_type_id=defect_type_id,
    )
