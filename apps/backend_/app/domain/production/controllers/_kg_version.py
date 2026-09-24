"""KG version catalog controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import msgspec
from litestar import Controller, Request, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.production.permissions import KgVersionPermission
from app.domain.production.schemas import (
    KgVersion,
    KgVersionCreate,
    KgVersionUpdate,
)
from app.domain.production.services import KgVersionService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

VersionId = Annotated[
    UUID,
    Parameter(title="KG version ID", description="The KG version to act on."),
]


class KgVersionController(Controller):
    """Hardware versions of KG units."""

    tags = ["KG catalogs"]  # noqa: RUF012
    path = "/kg/versions"
    dependencies = create_service_dependencies(
        KgVersionService,
        key="kg_versions_service",
        filters={
            "id_filter": UUID,
            "search": "code,name",
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "code",
            "sort_order": "asc",
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_version_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.KgVersion,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="kg_version",
            target_id=str(target.id),
            target_label=target.code,
            details=details,
            request=request,
        )

    @get(
        operation_id="ListKgVersions",
        guards=[requires_permission(KgVersionPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_kg_versions(
        self,
        kg_versions_service: NamedDependency[KgVersionService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[KgVersion]:
        results, total = await kg_versions_service.get_many_and_count(*filters, *archived_filter)

        return kg_versions_service.to_schema(
            results,
            total,
            filters,
            schema_type=KgVersion,
        )

    @get(
        operation_id="GetKgVersion",
        path="/{version_id:uuid}",
        guards=[requires_permission(KgVersionPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_kg_version(
        self,
        kg_versions_service: NamedDependency[KgVersionService],
        version_id: VersionId,
    ) -> KgVersion:
        db_obj = await kg_versions_service.get(version_id)

        return kg_versions_service.to_schema(db_obj, schema_type=KgVersion)

    @post(
        operation_id="CreateKgVersion",
        path="",
        guards=[requires_permission(KgVersionPermission.CREATE)],
        responses=error_responses(401, 403, 409),
    )
    async def create_kg_version(
        self,
        request: Request[m.User, Any, Any],
        kg_versions_service: NamedDependency[KgVersionService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: KgVersionCreate,
    ) -> KgVersion:
        db_obj = await kg_versions_service.create_version(data.to_dict())
        await self._log_version_action(
            request,
            audit_service,
            action="kg_version.created",
            target=db_obj,
        )

        return kg_versions_service.to_schema(db_obj, schema_type=KgVersion)

    @patch(
        operation_id="UpdateKgVersion",
        path="/{version_id:uuid}",
        guards=[requires_permission(KgVersionPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_kg_version(
        self,
        request: Request[m.User, Any, Any],
        data: KgVersionUpdate,
        kg_versions_service: NamedDependency[KgVersionService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        version_id: VersionId,
    ) -> KgVersion:
        db_obj = await kg_versions_service.update_version(version_id, data.to_dict())
        await self._log_version_action(
            request,
            audit_service,
            action="kg_version.updated",
            target=db_obj,
            details={
                "fields": [field for field in ("name", "description") if getattr(data, field) is not msgspec.UNSET]
            },
        )

        return kg_versions_service.to_schema(db_obj, schema_type=KgVersion)

    @post(
        operation_id="ArchiveKgVersion",
        path="/{version_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(KgVersionPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def archive_kg_version(
        self,
        request: Request[m.User, Any, Any],
        kg_versions_service: NamedDependency[KgVersionService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        version_id: VersionId,
    ) -> KgVersion:
        return await self._set_archived(
            request,
            kg_versions_service,
            audit_service,
            version_id,
            archived=True,
        )

    @post(
        operation_id="RestoreKgVersion",
        path="/{version_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(KgVersionPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_kg_version(
        self,
        request: Request[m.User, Any, Any],
        kg_versions_service: NamedDependency[KgVersionService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        version_id: VersionId,
    ) -> KgVersion:
        return await self._set_archived(
            request,
            kg_versions_service,
            audit_service,
            version_id,
            archived=False,
        )

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        kg_versions_service: KgVersionService,
        audit_service: AuditLogService,
        version_id: UUID,
        *,
        archived: bool,
    ) -> KgVersion:
        was_archived = (await kg_versions_service.get(version_id)).archived_at is not None
        db_obj = await kg_versions_service.set_archived(version_id, archived=archived)

        if was_archived != archived:
            await self._log_version_action(
                request,
                audit_service,
                action="kg_version.archived" if archived else "kg_version.restored",
                target=db_obj,
            )

        return kg_versions_service.to_schema(db_obj, schema_type=KgVersion)

    @delete(
        operation_id="DeleteKgVersion",
        path="/{version_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(KgVersionPermission.DELETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def delete_kg_version(
        self,
        request: Request[m.User, Any, Any],
        kg_versions_service: NamedDependency[KgVersionService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        version_id: VersionId,
    ) -> None:
        target = await kg_versions_service.delete_version(version_id)
        await self._log_version_action(
            request,
            audit_service,
            action="kg_version.deleted",
            target=target,
        )
