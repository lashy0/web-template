from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.domains.equipment.pak.permissions import PakPermission
from app.domains.quality.defects.schemas import DefectGroupSummaryResponse
from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission

from .exceptions import CheckNotFoundError
from .model import Check
from .schemas import PakTestListResponse, PakTestResponse
from .wiring import create_queries

router = APIRouter(tags=["pak"])


def _response(item: Check) -> PakTestResponse:
    return PakTestResponse(
        id=item.id,
        test_name=item.test_name,
        test_label=item.test_label,
        defect_group_id=item.defect_group_id,
        defect_group=DefectGroupSummaryResponse(
            id=item.defect_group.id,
            code=item.defect_group.code,
            name=item.defect_group.name,
            archived_at=item.defect_group.archived_at,
        ),
        last_seen_at=item.last_seen_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/tests", response_model=PakTestListResponse)
async def list_pak_tests(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.READ))],
    session_factory: SessionFactoryDep,
    q: str | None = None,
    defect_group_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "test_name", "test_label", "last_seen_at", "created_at", "updated_at"
    ] = "test_name",
    order: Literal["asc", "desc"] = "asc",
) -> PakTestListResponse:
    async with session_factory() as session:
        items, total = await create_queries(session).list(
            q=q,
            defect_group_id=defect_group_id,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )
    return PakTestListResponse(
        items=[_response(item) for item in items], total=total, page=page, page_size=page_size
    )


@router.get("/tests/{test_id}", response_model=PakTestResponse)
async def get_pak_test(
    test_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(PakPermission.READ))],
    session_factory: SessionFactoryDep,
) -> PakTestResponse:
    async with session_factory() as session:
        item = await create_queries(session).get(test_id)
    if item is None:
        raise CheckNotFoundError
    return _response(item)
