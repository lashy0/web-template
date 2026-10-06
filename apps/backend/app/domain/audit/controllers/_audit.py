"""Audit log controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.params import SkipValidation

from app.domain.audit.permissions import AuditPermission
from app.domain.audit.schemas import AuditLogEntry
from app.domain.audit.services import AuditLogService
from app.lib.authorization import requires_permission
from app.lib.deps import create_filter_dependencies
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination


class AuditController(Controller):
    """The audit log of user actions, newest first; entries are never changed."""

    tags = ["Audit"]  # noqa: RUF012
    path = "/audit"
    dependencies = create_filter_dependencies(
        {
            "pagination_type": "limit_offset",
            "pagination_size": 50,
            "created_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
            "in_fields": [
                FieldNameType(name="target_type", type_hint=str),
                FieldNameType(name="target_id", type_hint=str),
                FieldNameType(name="actor_id", type_hint=UUID),
                FieldNameType(name="action", type_hint=str),
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
        page = audit_service.to_schema(results, total, filters, schema_type=AuditLogEntry)

        current_labels = await audit_service.current_target_labels(results)

        for item in page.items:
            current = current_labels.get((item.target_type or "", item.target_id or ""))

            if current != item.target_label:
                item.target_current_label = current

        return page
