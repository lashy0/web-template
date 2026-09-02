from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.pak.deps import CurrentPakDep
from app.modules.verification.exceptions import VerificationSessionNotFoundError
from app.modules.verification.models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
)
from app.modules.verification.permissions import VerificationPermission
from app.modules.verification.schemas.common import (
    VerificationSessionDetailResponse,
    VerificationSessionListResponse,
    VerificationSessionResponse,
    VerificationStepResponse,
)
from app.modules.verification.schemas.machine import (
    CompleteVerificationSessionRequest,
    CompleteVerificationStepRequest,
    OpenVerificationSessionRequest,
    StartVerificationStepRequest,
)
from app.modules.verification.service import VerificationManagementService


router = APIRouter(prefix="/verification", tags=["verification"])


def _service(request: Request) -> VerificationManagementService:
    return cast(
        VerificationManagementService,
        request.app.state.verification_management,
    )


def _session_response(session: VerificationSession) -> VerificationSessionResponse:
    return VerificationSessionResponse(
        id=session.id,
        kg_dev_eui=session.kg_dev_eui,
        pak_id=session.pak_id,
        slot_no=session.slot_no,
        firmware_version=session.firmware_version,
        total_steps=session.total_steps,
        status=session.status,
        started_at=session.started_at,
        last_activity_at=session.last_activity_at,
        completed_at=session.completed_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _step_response(step: VerificationStep) -> VerificationStepResponse:
    return VerificationStepResponse(
        id=step.id,
        session_id=step.session_id,
        step_no=step.step_no,
        pak_test_id=step.pak_test_id,
        defect_group_id=step.defect_group_id,
        test_name=step.test_name,
        test_label=step.test_label,
        error_group_code=step.error_group_code,
        status=step.status,
        measurement_value=step.measurement_value,
        measurement_min_value=step.measurement_min_value,
        measurement_max_value=step.measurement_max_value,
        measurement_unit=step.measurement_unit,
        started_at=step.started_at,
        completed_at=step.completed_at,
        created_at=step.created_at,
        updated_at=step.updated_at,
    )


@router.get("/sessions", response_model=VerificationSessionListResponse)
async def list_sessions(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(VerificationPermission.READ))],
    request: Request,
    q: str | None = None,
    pak_id: UUID | None = None,
    status_filter: VerificationSessionStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "kg_dev_eui",
        "status",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ] = "started_at",
    order: Literal["asc", "desc"] = "desc",
) -> VerificationSessionListResponse:
    sessions, total = await _service(request).list(
        q=q,
        pak_id=pak_id,
        status=status_filter,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return VerificationSessionListResponse(
        items=[
            _session_response(session)
            for session in sessions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions/{session_id}", response_model=VerificationSessionDetailResponse)
async def get_session(
    session_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(VerificationPermission.READ))],
    request: Request,
) -> VerificationSessionDetailResponse:
    result = await _service(request).get_detail(session_id)

    if result is None:
        raise VerificationSessionNotFoundError

    session, steps = result

    response = _session_response(session)

    return VerificationSessionDetailResponse(
        **response.model_dump(),
        steps=[
            _step_response(step)
            for step in steps
        ],
    )


@router.post(
    "/sessions",
    response_model=VerificationSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_session(
    payload: OpenVerificationSessionRequest,
    pak: CurrentPakDep,
    request: Request,
) -> VerificationSessionResponse:
    session = await _service(request).open_session(
        pak=pak,
        kg_dev_eui=payload.kg_dev_eui,
        slot_no=payload.slot_no,
        firmware_version=payload.firmware_version,
        total_steps=payload.total_steps,
    )

    return _session_response(session)


@router.post(
    "/sessions/{session_id}/steps",
    response_model=VerificationStepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_step(
    session_id: UUID,
    payload: StartVerificationStepRequest,
    pak: CurrentPakDep,
    request: Request,
) -> VerificationStepResponse:
    step = await _service(request).start_step(
        pak=pak,
        session_id=session_id,
        step_no=payload.step_no,
        test_name=payload.test_name,
        test_label=payload.test_label,
        error_group_code=payload.error_group_code,
    )

    return _step_response(step)


@router.put(
    "/sessions/{session_id}/steps/{step_no}",
    response_model=VerificationStepResponse,
)
async def complete_step(
    session_id: UUID,
    step_no: int,
    payload: CompleteVerificationStepRequest,
    pak: CurrentPakDep,
    request: Request,
) -> VerificationStepResponse:
    step = await _service(request).complete_step(
        pak=pak,
        session_id=session_id,
        step_no=step_no,
        status=payload.status,
        measurement_value=payload.measurement_value,
        measurement_min_value=payload.measurement_min_value,
        measurement_max_value=payload.measurement_max_value,
        measurement_unit=payload.measurement_unit,
    )

    return _step_response(step)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=VerificationSessionResponse,
)
async def complete_session(
    session_id: UUID,
    payload: CompleteVerificationSessionRequest,
    pak: CurrentPakDep,
    request: Request,
) -> VerificationSessionResponse:
    session = await _service(request).complete_session(
        pak=pak,
        session_id=session_id,
        status=payload.status,
    )

    return _session_response(session)
