"""PAK check catalog controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from advanced_alchemy.filters import FilterTypes, NotNullFilter, NullFilter
from litestar import Controller, get
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, QueryParameter, SkipValidation

from app.domain.quality.permissions import VerificationPermission
from app.domain.quality.schemas import PakCheck
from app.domain.quality.services import PakCheckService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.service.pagination import OffsetPagination

CheckId = Annotated[
    UUID,
    Parameter(title="PAK check ID", description="The check to read."),
]


def provide_misconfigured_filter(
    misconfigured: Annotated[
        bool | None,
        QueryParameter(description="Only checks without (true) or with (false) an active defect group."),
    ] = None,
) -> list[FilterTypes]:
    if misconfigured is None:
        return []

    return [NullFilter("defect_group_id") if misconfigured else NotNullFilter("defect_group_id")]


class PakCheckController(Controller):
    """The checks PAKs run, recorded from their reports."""

    tags = ["Verification"]  # noqa: RUF012
    path = "/verification/checks"
    dependencies = create_service_dependencies(
        PakCheckService,
        key="pak_checks_service",
        filters={
            "id_filter": UUID,
            "search": "name,label,defect_group_code",
            "search_ignore_case": True,
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "name",
            "sort_order": "asc",
            "in_fields": [FieldNameType(name="defect_group_id", type_hint=UUID)],
        },
    )
    dependencies["misconfigured_filter"] = Provide(provide_misconfigured_filter, sync_to_thread=False)

    @get(
        operation_id="ListPakChecks",
        guards=[requires_permission(VerificationPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_pak_checks(
        self,
        pak_checks_service: NamedDependency[PakCheckService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        misconfigured_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[PakCheck]:
        results, total = await pak_checks_service.get_many_and_count(*filters, *misconfigured_filter)

        return pak_checks_service.to_schema(results, total, filters, schema_type=PakCheck)

    @get(
        operation_id="GetPakCheck",
        path="/{check_id:uuid}",
        guards=[requires_permission(VerificationPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_pak_check(
        self,
        pak_checks_service: NamedDependency[PakCheckService],
        check_id: CheckId,
    ) -> PakCheck:
        db_obj = await pak_checks_service.get(check_id)

        return pak_checks_service.to_schema(db_obj, schema_type=PakCheck)
