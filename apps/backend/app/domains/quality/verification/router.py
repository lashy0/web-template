from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.domains.equipment.pak.deps import CurrentPakDep
from app.domains.equipment.pak.schemas import PakDeviceSummaryResponse
from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission

from .exceptions import VerificationSessionNotFoundError
from .model import VerificationSession, VerificationSessionStatus, VerificationStep
from .permissions import VerificationPermission
from .schemas import (
    CompleteVerificationSessionRequest,
    CompleteVerificationStepRequest,
    OpenVerificationSessionRequest,
    StartVerificationStepRequest,
    VerificationSessionDetailResponse,
    VerificationSessionListResponse,
    VerificationSessionResponse,
    VerificationStepResponse,
)
from .transaction import verification_transaction
from .wiring import (
    KgPortFactoryDep,
    PakAdapterDep,
    ReopenInactivityDep,
    complete_session_command,
    complete_step_command,
    create_queries,
    start_session_command,
    start_step_command,
)

router = APIRouter(prefix="/verification", tags=["verification"])
machine_router = APIRouter(prefix="/verification", tags=["verification-machine"])


def _session_response(item: VerificationSession) -> VerificationSessionResponse:
    return VerificationSessionResponse(
        id=item.id,
        kg_dev_eui=item.kg_dev_eui,
        pak_id=item.pak_id,
        pak=PakDeviceSummaryResponse(id=item.pak.id, code=item.pak.code, kind=item.pak.kind),
        slot_no=item.slot_no,
        firmware_version=item.firmware_version,
        total_steps=item.total_steps,
        status=item.status,
        started_at=item.started_at,
        last_activity_at=item.last_activity_at,
        completed_at=item.completed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _step_response(item: VerificationStep) -> VerificationStepResponse:
    return VerificationStepResponse(
        id=item.id,
        session_id=item.session_id,
        step_no=item.step_no,
        pak_test_id=item.pak_test_id,
        defect_group_id=item.defect_group_id,
        test_name=item.test_name,
        test_label=item.test_label,
        error_group_code=item.error_group_code,
        status=item.status,
        measurement_value=item.measurement_value,
        measurement_min_value=item.measurement_min_value,
        measurement_max_value=item.measurement_max_value,
        measurement_unit=item.measurement_unit,
        started_at=item.started_at,
        completed_at=item.completed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/sessions", response_model=VerificationSessionListResponse)
async def list_sessions(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(VerificationPermission.READ))],
    session_factory: SessionFactoryDep,
    q: str | None = None,
    pak_id: UUID | None = None,
    status_filter: VerificationSessionStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "kg_dev_eui", "status", "started_at", "completed_at", "created_at", "updated_at"
    ] = "started_at",
    order: Literal["asc", "desc"] = "desc",
) -> VerificationSessionListResponse:
    async with session_factory() as session:
        items, total = await create_queries(session).list(
            q=q,
            pak_id=pak_id,
            status=status_filter,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )
    return VerificationSessionListResponse(
        items=[_session_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions/{session_id}", response_model=VerificationSessionDetailResponse)
async def get_session(
    session_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(VerificationPermission.READ))],
    session_factory: SessionFactoryDep,
) -> VerificationSessionDetailResponse:
    async with session_factory() as session:
        result = await create_queries(session).get_detail(session_id)
    if result is None:
        raise VerificationSessionNotFoundError
    item, steps = result
    return VerificationSessionDetailResponse(
        **_session_response(item).model_dump(), steps=[_step_response(step) for step in steps]
    )


@machine_router.post(
    "/sessions", response_model=VerificationSessionResponse, status_code=status.HTTP_201_CREATED
)
async def open_session(
    payload: OpenVerificationSessionRequest,
    pak: CurrentPakDep,
    session_factory: SessionFactoryDep,
    kg_port_factory: KgPortFactoryDep,
    pak_adapter: PakAdapterDep,
    reopen_inactivity: ReopenInactivityDep,
) -> VerificationSessionResponse:
    async with verification_transaction(session_factory) as session:
        item = await start_session_command(session, kg_port_factory, reopen_inactivity).execute(
            pak=pak_adapter(pak), **payload.model_dump()
        )
    return _session_response(item)


@machine_router.post(
    "/sessions/{session_id}/steps",
    response_model=VerificationStepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_step(
    session_id: UUID,
    payload: StartVerificationStepRequest,
    pak: CurrentPakDep,
    session_factory: SessionFactoryDep,
    pak_adapter: PakAdapterDep,
) -> VerificationStepResponse:
    async with verification_transaction(session_factory) as session:
        item = await start_step_command(session).execute(
            pak=pak_adapter(pak), session_id=session_id, **payload.model_dump()
        )
    return _step_response(item)


@machine_router.put(
    "/sessions/{session_id}/steps/{step_no}", response_model=VerificationStepResponse
)
async def complete_step(
    session_id: UUID,
    step_no: int,
    payload: CompleteVerificationStepRequest,
    pak: CurrentPakDep,
    session_factory: SessionFactoryDep,
    pak_adapter: PakAdapterDep,
) -> VerificationStepResponse:
    async with verification_transaction(session_factory) as session:
        item = await complete_step_command(session).execute(
            pak=pak_adapter(pak),
            session_id=session_id,
            step_no=step_no,
            **payload.model_dump(),
        )
    return _step_response(item)


@machine_router.post("/sessions/{session_id}/complete", response_model=VerificationSessionResponse)
async def complete_session(
    session_id: UUID,
    payload: CompleteVerificationSessionRequest,
    pak: CurrentPakDep,
    session_factory: SessionFactoryDep,
    pak_adapter: PakAdapterDep,
) -> VerificationSessionResponse:
    async with verification_transaction(session_factory) as session:
        item = await complete_session_command(session).execute(
            pak=pak_adapter(pak), session_id=session_id, status=payload.status
        )
    return _session_response(item)
