from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.contexts.equipment.pak.permissions import PakPermission
from app.contexts.quality.defects.schemas import DefectGroupSummaryResponse

from .exceptions import PakTestNotFoundError
from .model import PakTest
from .queries import PakTestQueries
from .repository import PakTestRepository
from .schemas import PakTestListResponse, PakTestResponse

router = APIRouter(tags=["pak"])


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


def _response(item: PakTest) -> PakTestResponse:
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
    request: Request,
    q: str | None = None,
    defect_group_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "test_name", "test_label", "last_seen_at", "created_at", "updated_at"
    ] = "test_name",
    order: Literal["asc", "desc"] = "asc",
) -> PakTestListResponse:
    async with _session_factory(request)() as session:
        items, total = await PakTestQueries(PakTestRepository(session)).list(
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
    request: Request,
) -> PakTestResponse:
    async with _session_factory(request)() as session:
        item = await PakTestQueries(PakTestRepository(session)).get(test_id)
    if item is None:
        raise PakTestNotFoundError
    return _response(item)
