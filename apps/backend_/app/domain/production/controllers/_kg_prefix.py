"""DevEUI prefix catalog controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from litestar import Controller, Request, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.production.permissions import KgPrefixPermission
from app.domain.production.schemas import (
    KgPrefix,
    KgPrefixCreate,
    KgPrefixUpdate,
)
from app.domain.production.services import KgPrefixService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

PrefixId = Annotated[
    UUID,
    Parameter(title="DevEUI prefix ID", description="The DevEUI prefix to act on."),
]


class KgPrefixController(Controller):
    """DevEUI prefixes that KG units are allocated from."""

    tags = ["KG catalogs"]  # noqa: RUF012
    path = "/kg/prefixes"
    dependencies = create_service_dependencies(
        KgPrefixService,
        key="kg_prefixes_service",
        filters={
            "id_filter": UUID,
            "search": "prefix,short_code,name",
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "prefix",
            "sort_order": "asc",
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_prefix_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.KgPrefix,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="kg_prefix",
            target_id=str(target.id),
            target_label=target.prefix,
            details=details,
            request=request,
        )

    @get(
        operation_id="ListKgPrefixes",
        guards=[requires_permission(KgPrefixPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_kg_prefixes(
        self,
        kg_prefixes_service: NamedDependency[KgPrefixService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[KgPrefix]:
        results, total = await kg_prefixes_service.get_many_and_count(*filters, *archived_filter)

        return kg_prefixes_service.to_schema(
            results,
            total,
            filters,
            schema_type=KgPrefix,
        )

    @get(
        operation_id="GetKgPrefix",
        path="/{prefix_id:uuid}",
        guards=[requires_permission(KgPrefixPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_kg_prefix(
        self,
        kg_prefixes_service: NamedDependency[KgPrefixService],
        prefix_id: PrefixId,
    ) -> KgPrefix:
        db_obj = await kg_prefixes_service.get(prefix_id)

        return kg_prefixes_service.to_schema(db_obj, schema_type=KgPrefix)

    @post(
        operation_id="CreateKgPrefix",
        path="",
        guards=[requires_permission(KgPrefixPermission.CREATE)],
        responses=error_responses(401, 403, 409),
    )
    async def create_kg_prefix(
        self,
        request: Request[m.User, Any, Any],
        kg_prefixes_service: NamedDependency[KgPrefixService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: KgPrefixCreate,
    ) -> KgPrefix:
        db_obj = await kg_prefixes_service.create_prefix(data.to_dict())
        await self._log_prefix_action(
            request,
            audit_service,
            action="kg_prefix.created",
            target=db_obj,
            details={"short_code": db_obj.short_code},
        )

        return kg_prefixes_service.to_schema(db_obj, schema_type=KgPrefix)

    @patch(
        operation_id="UpdateKgPrefix",
        path="/{prefix_id:uuid}",
        guards=[requires_permission(KgPrefixPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_kg_prefix(
        self,
        request: Request[m.User, Any, Any],
        data: KgPrefixUpdate,
        kg_prefixes_service: NamedDependency[KgPrefixService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        prefix_id: PrefixId,
    ) -> KgPrefix:
        db_obj = await kg_prefixes_service.update_prefix(prefix_id, data.to_dict())
        await self._log_prefix_action(
            request,
            audit_service,
            action="kg_prefix.updated",
            target=db_obj,
            details={"fields": ["name"]},
        )

        return kg_prefixes_service.to_schema(db_obj, schema_type=KgPrefix)

    @post(
        operation_id="ArchiveKgPrefix",
        path="/{prefix_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(KgPrefixPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def archive_kg_prefix(
        self,
        request: Request[m.User, Any, Any],
        kg_prefixes_service: NamedDependency[KgPrefixService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        prefix_id: PrefixId,
    ) -> KgPrefix:
        return await self._set_archived(
            request,
            kg_prefixes_service,
            audit_service,
            prefix_id,
            archived=True,
        )

    @post(
        operation_id="RestoreKgPrefix",
        path="/{prefix_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(KgPrefixPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_kg_prefix(
        self,
        request: Request[m.User, Any, Any],
        kg_prefixes_service: NamedDependency[KgPrefixService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        prefix_id: PrefixId,
    ) -> KgPrefix:
        return await self._set_archived(
            request,
            kg_prefixes_service,
            audit_service,
            prefix_id,
            archived=False,
        )

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        kg_prefixes_service: KgPrefixService,
        audit_service: AuditLogService,
        prefix_id: UUID,
        *,
        archived: bool,
    ) -> KgPrefix:
        was_archived = (await kg_prefixes_service.get(prefix_id)).archived_at is not None
        db_obj = await kg_prefixes_service.set_archived(prefix_id, archived=archived)

        if was_archived != archived:
            await self._log_prefix_action(
                request,
                audit_service,
                action="kg_prefix.archived" if archived else "kg_prefix.restored",
                target=db_obj,
            )

        return kg_prefixes_service.to_schema(db_obj, schema_type=KgPrefix)

    @delete(
        operation_id="DeleteKgPrefix",
        path="/{prefix_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(KgPrefixPermission.DELETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def delete_kg_prefix(
        self,
        request: Request[m.User, Any, Any],
        kg_prefixes_service: NamedDependency[KgPrefixService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        prefix_id: PrefixId,
    ) -> None:
        target = await kg_prefixes_service.delete_prefix(prefix_id)
        await self._log_prefix_action(
            request,
            audit_service,
            action="kg_prefix.deleted",
            target=target,
        )
