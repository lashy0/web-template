from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..permissions import KgPermission
from ..schemas import (
    CreateKgVersionRequest,
    KgVersionListResponse,
    KgVersionResponse,
    UpdateKgVersionArchivedRequest,
    UpdateKgVersionRequest,
)
from .common import _version_response, _version_service

router = APIRouter()


@router.get("/versions", response_model=KgVersionListResponse)
async def list_kg_versions(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(KgPermission.VERSION_READ)),
    ],
    request: Request,
    q: str | None = None,
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: Literal[
        "code",
        "name",
        "description",
        "created_at",
        "updated_at",
        "archived_at",
    ] = "code",
    sort_order: Literal["asc", "desc"] = "asc",
) -> KgVersionListResponse:
    items, total = await _version_service(request).list(
        q=q,
        archived=archived,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return KgVersionListResponse(
        items=[
            _version_response(item, batch_count=batch_count)
            for item, batch_count in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/versions",
    response_model=KgVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_kg_version(
    payload: CreateKgVersionRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_CREATE))
    ],
    request: Request,
) -> KgVersionResponse:
    return _version_response(
        await _version_service(request).create(
            actor=principal,
            **payload.model_dump(),
        )
    )


@router.patch("/versions/{version_id}", response_model=KgVersionResponse)
async def update_kg_version(
    version_id: UUID,
    payload: UpdateKgVersionRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_UPDATE))
    ],
    request: Request,
) -> KgVersionResponse:
    return _version_response(
        await _version_service(request).update(
            actor=principal,
            version_id=version_id,
            updates=payload.model_dump(exclude_unset=True),
        )
    )


@router.put("/versions/{version_id}/archived", response_model=KgVersionResponse)
async def update_kg_version_archived(
    version_id: UUID,
    payload: UpdateKgVersionArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_ARCHIVE))
    ],
    request: Request,
) -> KgVersionResponse:
    return _version_response(
        await _version_service(request).set_archived(
            actor=principal,
            version_id=version_id,
            archived=payload.archived,
        )
    )


@router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kg_version(
    version_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(KgPermission.VERSION_DELETE))
    ],
    request: Request,
) -> None:
    await _version_service(request).delete(actor=principal, version_id=version_id)
