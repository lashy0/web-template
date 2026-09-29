"""Machine API through which PAKs report verification sessions."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from litestar import Controller, Request, post, put
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.config import VerificationSettings
from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.pak.deps import provide_current_pak, provide_pak_devices_service
from app.domain.quality.schemas import (
    VerificationSession,
    VerificationSessionComplete,
    VerificationSessionOpen,
    VerificationStep,
    VerificationStepComplete,
    VerificationStepStart,
)
from app.domain.quality.services import (
    CheckObservation,
    PakCheckService,
    VerificationSessionService,
)
from app.lib.deps import create_service_provider
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

SessionId = Annotated[
    UUID,
    Parameter(title="Verification session ID", description="A session the calling PAK opened."),
]
StepNo = Annotated[
    int,
    Parameter(title="Step number", description="Position of the check in the session, from 1.", ge=1),
]

_MACHINE_ERRORS = (401, 403, 404, 409)


class MachineVerificationController(Controller):
    """Verification reports of the calling PAK, authenticated by its Hydra access token.

    Every request may be repeated: a report the server already has is answered
    with the current state instead of an error.
    """

    tags = ["PAK machine API"]  # noqa: RUF012
    path = "/machine/verification/sessions"
    opt = {"exclude_from_auth": True}  # noqa: RUF012 - authenticated by `current_pak` instead
    dependencies = {  # noqa: RUF012
        "pak_devices_service": Provide(provide_pak_devices_service),
        "current_pak": Provide(provide_current_pak),
        "verification_sessions_service": Provide(create_service_provider(VerificationSessionService)),
        "pak_checks_service": Provide(create_service_provider(PakCheckService)),
        "audit_service": Provide(provide_audit_log_service),
    }

    @post(
        operation_id="OpenVerificationSession",
        path="",
        status_code=HTTP_201_CREATED,
        responses=error_responses(*_MACHINE_ERRORS),
    )
    async def open_verification_session(
        self,
        current_pak: NamedDependency[m.PakDevice],
        verification_sessions_service: NamedDependency[VerificationSessionService],
        verification_settings: NamedDependency[VerificationSettings],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: VerificationSessionOpen,
    ) -> VerificationSession:
        """Start verifying a KG unit in a slot, or resume its session running there."""
        db_obj = await verification_sessions_service.open_session(
            current_pak,
            data,
            reopen_inactivity=verification_settings.reopen_inactivity,
        )

        return verification_sessions_service.to_schema(db_obj, schema_type=VerificationSession)

    @post(
        operation_id="StartVerificationStep",
        path="/{session_id:uuid}/steps",
        status_code=HTTP_201_CREATED,
        responses=error_responses(*_MACHINE_ERRORS),
    )
    async def start_verification_step(
        self,
        request: Request[Any, Any, Any],
        current_pak: NamedDependency[m.PakDevice],
        verification_sessions_service: NamedDependency[VerificationSessionService],
        pak_checks_service: NamedDependency[PakCheckService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        session_id: SessionId,
        data: VerificationStepStart,
    ) -> VerificationStep:
        """Start a check of the session; the check is recorded in the check catalog."""
        step, observation = await verification_sessions_service.start_step(
            current_pak,
            session_id,
            data,
            checks=pak_checks_service,
        )

        if observation is not None:
            await self._log_check_changes(
                request,
                audit_service,
                current_pak,
                observation,
            )

        return verification_sessions_service.to_schema(step, schema_type=VerificationStep)

    @put(
        operation_id="CompleteVerificationStep",
        path="/{session_id:uuid}/steps/{step_no:int}",
        status_code=HTTP_200_OK,
        responses=error_responses(*_MACHINE_ERRORS),
    )
    async def complete_verification_step(
        self,
        current_pak: NamedDependency[m.PakDevice],
        verification_sessions_service: NamedDependency[VerificationSessionService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        session_id: SessionId,
        step_no: StepNo,
        data: VerificationStepComplete,
    ) -> VerificationStep:
        """Report the result of the running check."""
        step = await verification_sessions_service.complete_step(
            current_pak,
            session_id,
            step_no,
            data,
        )

        return verification_sessions_service.to_schema(step, schema_type=VerificationStep)

    @post(
        operation_id="CompleteVerificationSession",
        path="/{session_id:uuid}/complete",
        status_code=HTTP_200_OK,
        responses=error_responses(*_MACHINE_ERRORS),
    )
    async def complete_verification_session(
        self,
        current_pak: NamedDependency[m.PakDevice],
        verification_sessions_service: NamedDependency[VerificationSessionService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        session_id: SessionId,
        data: VerificationSessionComplete,
    ) -> VerificationSession:
        """Finish the session; on an OTK-line PAK a pass or fail sets the KG unit's OTK status."""
        db_obj = await verification_sessions_service.complete_session(current_pak, session_id, data)

        return verification_sessions_service.to_schema(db_obj, schema_type=VerificationSession)

    @staticmethod
    async def _log_check_changes(
        request: Request[Any, Any, Any],
        audit_service: AuditLogService,
        pak: m.PakDevice,
        observation: CheckObservation,
    ) -> None:
        if not observation.created and not observation.changes:
            return

        check = observation.check
        await audit_service.log_action(
            action="pak_check.created" if observation.created else "pak_check.updated",
            actor_login=pak.code,
            target_type="pak_check",
            target_id=str(check.id),
            target_label=check.label,
            details={
                "pak_id": str(pak.id),
                "name": check.name,
                **(
                    {"defect_group_code": check.defect_group_code}
                    if observation.created
                    else {"changes": observation.changes}
                ),
            },
            request=request,
        )
