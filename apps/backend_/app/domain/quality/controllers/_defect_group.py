"""Defect group controllers."""

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
from app.domain.quality.permissions import DefectPermission
from app.domain.quality.schemas import DefectGroup, DefectGroupCreate, DefectGroupUpdate
from app.domain.quality.services import DefectGroupService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

GroupId = Annotated[
    UUID,
    Parameter(title="Defect group ID", description="The defect group to act on."),
]


class DefectGroupController(Controller):
    """Groups of the defect catalog."""

    tags = ["Defect catalog"]  # noqa: RUF012
    path = "/defects/groups"
    dependencies = create_service_dependencies(
        DefectGroupService,
        key="defect_groups_service",
        filters={
            "id_filter": UUID,
            "search": "code,name",
            "search_ignore_case": True,
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
    async def _log_group_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.DefectGroup,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="defect_group",
            target_id=str(target.id),
            target_label=target.code,
            details=details,
            request=request,
        )

    @get(
        operation_id="ListDefectGroups",
        guards=[requires_permission(DefectPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_defect_groups(
        self,
        defect_groups_service: NamedDependency[DefectGroupService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[DefectGroup]:
        results, total = await defect_groups_service.get_many_and_count(*filters, *archived_filter)

        return defect_groups_service.to_schema(results, total, filters, schema_type=DefectGroup)

    @get(
        operation_id="GetDefectGroup",
        path="/{group_id:uuid}",
        guards=[requires_permission(DefectPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_defect_group(
        self,
        defect_groups_service: NamedDependency[DefectGroupService],
        group_id: GroupId,
    ) -> DefectGroup:
        db_obj = await defect_groups_service.get(group_id)

        return defect_groups_service.to_schema(db_obj, schema_type=DefectGroup)

    @post(
        operation_id="CreateDefectGroup",
        path="",
        guards=[requires_permission(DefectPermission.CREATE)],
        responses=error_responses(401, 403, 409),
    )
    async def create_defect_group(
        self,
        request: Request[m.User, Any, Any],
        defect_groups_service: NamedDependency[DefectGroupService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: DefectGroupCreate,
    ) -> DefectGroup:
        db_obj = await defect_groups_service.create_group(data.to_dict())
        await self._log_group_action(request, audit_service, action="defect_group.created", target=db_obj)

        return defect_groups_service.to_schema(db_obj, schema_type=DefectGroup)

    @patch(
        operation_id="UpdateDefectGroup",
        path="/{group_id:uuid}",
        guards=[requires_permission(DefectPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_defect_group(
        self,
        request: Request[m.User, Any, Any],
        data: DefectGroupUpdate,
        defect_groups_service: NamedDependency[DefectGroupService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        group_id: GroupId,
    ) -> DefectGroup:
        db_obj = await defect_groups_service.update_group(group_id, data.to_dict())
        await self._log_group_action(
            request,
            audit_service,
            action="defect_group.updated",
            target=db_obj,
            details={
                "fields": [field for field in ("name", "description") if getattr(data, field) is not msgspec.UNSET]
            },
        )

        return defect_groups_service.to_schema(db_obj, schema_type=DefectGroup)

    @post(
        operation_id="ArchiveDefectGroup",
        path="/{group_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(DefectPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def archive_defect_group(
        self,
        request: Request[m.User, Any, Any],
        defect_groups_service: NamedDependency[DefectGroupService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        group_id: GroupId,
    ) -> DefectGroup:
        return await self._set_archived(
            request,
            defect_groups_service,
            audit_service,
            group_id,
            archived=True,
        )

    @post(
        operation_id="RestoreDefectGroup",
        path="/{group_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(DefectPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_defect_group(
        self,
        request: Request[m.User, Any, Any],
        defect_groups_service: NamedDependency[DefectGroupService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        group_id: GroupId,
    ) -> DefectGroup:
        return await self._set_archived(
            request,
            defect_groups_service,
            audit_service,
            group_id,
            archived=False,
        )

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        defect_groups_service: DefectGroupService,
        audit_service: AuditLogService,
        group_id: UUID,
        *,
        archived: bool,
    ) -> DefectGroup:
        was_archived = (await defect_groups_service.get(group_id)).archived_at is not None
        db_obj = await defect_groups_service.set_archived(group_id, archived=archived)

        if was_archived != archived:
            await self._log_group_action(
                request,
                audit_service,
                action="defect_group.archived" if archived else "defect_group.restored",
                target=db_obj,
            )

        return defect_groups_service.to_schema(db_obj, schema_type=DefectGroup)

    @delete(
        operation_id="DeleteDefectGroup",
        path="/{group_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(DefectPermission.DELETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def delete_defect_group(
        self,
        request: Request[m.User, Any, Any],
        defect_groups_service: NamedDependency[DefectGroupService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        group_id: GroupId,
    ) -> None:
        target = await defect_groups_service.delete_group(group_id)
        await self._log_group_action(
            request,
            audit_service,
            action="defect_group.deleted",
            target=target,
        )
