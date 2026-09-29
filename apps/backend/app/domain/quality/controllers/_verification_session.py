"""Verification session controllers for users."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.params import Parameter, SkipValidation

from app.db.enums import PakDeviceKind, VerificationSessionStatus
from app.domain.quality.permissions import VerificationPermission
from app.domain.quality.schemas import VerificationSession, VerificationSessionDetail
from app.domain.quality.services import VerificationSessionService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

SessionId = Annotated[
    UUID,
    Parameter(title="Verification session ID", description="The session to read."),
]


class VerificationSessionController(Controller):
    """Verification history; PAKs write it through the machine API."""

    tags = ["Verification"]  # noqa: RUF012
    path = "/verification/sessions"
    dependencies = create_service_dependencies(
        VerificationSessionService,
        key="verification_sessions_service",
        filters={
            "id_filter": UUID,
            "search": "dev_eui",
            "search_ignore_case": True,
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "started_at",
            "sort_order": "desc",
            "in_fields": [
                FieldNameType(name="batch_id", type_hint=UUID),
                FieldNameType(name="pak_id", type_hint=UUID),
                FieldNameType(name="pak_kind", type_hint=PakDeviceKind),
                FieldNameType(name="status", type_hint=VerificationSessionStatus),
            ],
        },
    )

    @get(
        operation_id="ListVerificationSessions",
        guards=[requires_permission(VerificationPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_verification_sessions(
        self,
        verification_sessions_service: NamedDependency[VerificationSessionService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[VerificationSession]:
        results, total = await verification_sessions_service.get_many_and_count(*filters)

        return verification_sessions_service.to_schema(
            results,
            total,
            filters,
            schema_type=VerificationSession,
        )

    @get(
        operation_id="GetVerificationSession",
        path="/{session_id:uuid}",
        guards=[requires_permission(VerificationPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_verification_session(
        self,
        verification_sessions_service: NamedDependency[VerificationSessionService],
        session_id: SessionId,
    ) -> VerificationSessionDetail:
        db_obj = await verification_sessions_service.get_with_steps(session_id)

        return verification_sessions_service.to_schema(db_obj, schema_type=VerificationSessionDetail)
