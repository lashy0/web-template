"""Defect type controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import msgspec
from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, Request, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.quality.permissions import DefectPermission
from app.domain.quality.schemas import DefectType, DefectTypeCreate, DefectTypeUpdate
from app.domain.quality.services import DefectTypeService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

TypeId = Annotated[
    UUID,
    Parameter(title="Defect type ID", description="The defect type to act on."),
]

_UPDATABLE_FIELDS = ("name", "description", "possible_cause", "engineer_action")


class DefectTypeController(Controller):
    """Types of the defect catalog."""

    tags = ["Defect catalog"]  # noqa: RUF012
    path = "/defects/types"
    dependencies = create_service_dependencies(
        DefectTypeService,
        key="defect_types_service",
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
            "in_fields": [FieldNameType(name="group_id", type_hint=UUID)],
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_type_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.DefectType,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="defect_type",
            target_id=str(target.id),
            target_label=target.code,
            details=details,
            request=request,
        )

    @get(
        operation_id="ListDefectTypes",
        guards=[requires_permission(DefectPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_defect_types(
        self,
        defect_types_service: NamedDependency[DefectTypeService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[DefectType]:
        results, total = await defect_types_service.get_many_and_count(*filters, *archived_filter)

        return defect_types_service.to_schema(results, total, filters, schema_type=DefectType)

    @get(
        operation_id="GetDefectType",
        path="/{type_id:uuid}",
        guards=[requires_permission(DefectPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_defect_type(
        self,
        defect_types_service: NamedDependency[DefectTypeService],
        type_id: TypeId,
    ) -> DefectType:
        db_obj = await defect_types_service.get(type_id)

        return defect_types_service.to_schema(db_obj, schema_type=DefectType)

    @post(
        operation_id="CreateDefectType",
        path="",
        guards=[requires_permission(DefectPermission.CREATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def create_defect_type(
        self,
        request: Request[m.User, Any, Any],
        defect_types_service: NamedDependency[DefectTypeService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: DefectTypeCreate,
    ) -> DefectType:
        db_obj = await defect_types_service.create_type(data)
        await self._log_type_action(
            request,
            audit_service,
            action="defect_type.created",
            target=db_obj,
            details={"group_id": str(db_obj.group_id)},
        )

        return defect_types_service.to_schema(db_obj, schema_type=DefectType)

    @patch(
        operation_id="UpdateDefectType",
        path="/{type_id:uuid}",
        guards=[requires_permission(DefectPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_defect_type(
        self,
        request: Request[m.User, Any, Any],
        data: DefectTypeUpdate,
        defect_types_service: NamedDependency[DefectTypeService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        type_id: TypeId,
    ) -> DefectType:
        db_obj = await defect_types_service.update_type(type_id, data.to_dict())
        await self._log_type_action(
            request,
            audit_service,
            action="defect_type.updated",
            target=db_obj,
            details={"fields": [field for field in _UPDATABLE_FIELDS if getattr(data, field) is not msgspec.UNSET]},
        )

        return defect_types_service.to_schema(db_obj, schema_type=DefectType)

    @post(
        operation_id="ArchiveDefectType",
        path="/{type_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(DefectPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def archive_defect_type(
        self,
        request: Request[m.User, Any, Any],
        defect_types_service: NamedDependency[DefectTypeService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        type_id: TypeId,
    ) -> DefectType:
        return await self._set_archived(
            request,
            defect_types_service,
            audit_service,
            type_id,
            archived=True,
        )

    @post(
        operation_id="RestoreDefectType",
        path="/{type_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(DefectPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def restore_defect_type(
        self,
        request: Request[m.User, Any, Any],
        defect_types_service: NamedDependency[DefectTypeService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        type_id: TypeId,
    ) -> DefectType:
        return await self._set_archived(
            request,
            defect_types_service,
            audit_service,
            type_id,
            archived=False,
        )

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        defect_types_service: DefectTypeService,
        audit_service: AuditLogService,
        type_id: UUID,
        *,
        archived: bool,
    ) -> DefectType:
        was_archived = (await defect_types_service.get(type_id)).archived_at is not None
        db_obj = await defect_types_service.set_archived(type_id, archived=archived)

        if was_archived != archived:
            await self._log_type_action(
                request,
                audit_service,
                action="defect_type.archived" if archived else "defect_type.restored",
                target=db_obj,
            )

        return defect_types_service.to_schema(db_obj, schema_type=DefectType)

    @delete(
        operation_id="DeleteDefectType",
        path="/{type_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(DefectPermission.DELETE)],
        responses=error_responses(401, 403, 404),
    )
    async def delete_defect_type(
        self,
        request: Request[m.User, Any, Any],
        defect_types_service: NamedDependency[DefectTypeService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        type_id: TypeId,
    ) -> None:
        target = await defect_types_service.delete_type(type_id)
        await self._log_type_action(
            request,
            audit_service,
            action="defect_type.deleted",
            target=target,
            details={"group_id": str(target.group_id)},
        )
