"""Audit log controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.params import SkipValidation

from app.domain.admin.permissions import AuditPermission
from app.domain.admin.schemas import AuditLogEntry
from app.domain.admin.services import AuditLogService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination


class AuditController(Controller):
    """The audit log of user actions, newest first; entries are never changed."""

    tags = ["Audit"]  # noqa: RUF012
    path = "/audit"
    dependencies = create_service_dependencies(
        AuditLogService,
        key="audit_service",
        filters={
            "pagination_type": "limit_offset",
            "pagination_size": 50,
            "created_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
            "in_fields": [
                FieldNameType(name="target_type", type_hint=str),
                FieldNameType(name="target_id", type_hint=str),
                FieldNameType(name="actor_id", type_hint=UUID),
            ],
        },
    )

    @get(
        operation_id="ListAuditEntries",
        guards=[requires_permission(AuditPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_audit_entries(
        self,
        audit_service: NamedDependency[AuditLogService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[AuditLogEntry]:
        results, total = await audit_service.get_many_and_count(*filters)

        return audit_service.to_schema(results, total, filters, schema_type=AuditLogEntry)
