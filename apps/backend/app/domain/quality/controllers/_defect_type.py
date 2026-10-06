"""Defect type controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.domain.audit.changes import ChangeRecorder
from app.domain.quality.events import DefectTypeChanged
from app.domain.quality.permissions import DefectPermission
from app.domain.quality.schemas import DefectType, DefectTypeCreate, DefectTypeUpdate
from app.domain.quality.services import DefectTypeService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

TypeId = Annotated[
    UUID,
    Parameter(title="Defect type ID", description="The defect type to act on."),
]

_AUDIT_FIELDS = same_fields("name", "description", "possible_cause", "engineer_action")
"""Fields the ``updated`` audit entries compare."""


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
        defect_types_service: NamedDependency[DefectTypeService],
        changes: NamedDependency[ChangeRecorder],
        data: DefectTypeCreate,
    ) -> DefectType:
        db_obj = await defect_types_service.create_type(data)
        await changes.record(
            "defect_type.created",
            db_obj,
            event=DefectTypeChanged(type_id=db_obj.id),
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
        data: DefectTypeUpdate,
        defect_types_service: NamedDependency[DefectTypeService],
        changes: NamedDependency[ChangeRecorder],
        type_id: TypeId,
    ) -> DefectType:
        before = snapshot(await defect_types_service.get(type_id), _AUDIT_FIELDS)
        db_obj = await defect_types_service.update_type(
            type_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )

        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await changes.record(
                "defect_type.updated",
                db_obj,
                event=DefectTypeChanged(type_id=db_obj.id),
                details=details,
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
        defect_types_service: NamedDependency[DefectTypeService],
        changes: NamedDependency[ChangeRecorder],
        type_id: TypeId,
    ) -> DefectType:
        return await self._set_archived(defect_types_service, changes, type_id, archived=True)

    @post(
        operation_id="RestoreDefectType",
        path="/{type_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(DefectPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def restore_defect_type(
        self,
        defect_types_service: NamedDependency[DefectTypeService],
        changes: NamedDependency[ChangeRecorder],
        type_id: TypeId,
    ) -> DefectType:
        return await self._set_archived(defect_types_service, changes, type_id, archived=False)

    @staticmethod
    async def _set_archived(
        defect_types_service: DefectTypeService,
        changes: ChangeRecorder,
        type_id: UUID,
        *,
        archived: bool,
    ) -> DefectType:
        was_archived = (await defect_types_service.get(type_id)).archived_at is not None
        db_obj = await defect_types_service.set_archived(type_id, archived=archived)

        if was_archived != archived:
            await changes.record(
                "defect_type.archived" if archived else "defect_type.restored",
                db_obj,
                event=DefectTypeChanged(type_id=db_obj.id),
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
        defect_types_service: NamedDependency[DefectTypeService],
        changes: NamedDependency[ChangeRecorder],
        type_id: TypeId,
    ) -> None:
        target = await defect_types_service.delete_type(type_id)
        await changes.record(
            "defect_type.deleted",
            target,
            event=DefectTypeChanged(type_id=target.id),
            details={"group_id": str(target.group_id)},
        )
