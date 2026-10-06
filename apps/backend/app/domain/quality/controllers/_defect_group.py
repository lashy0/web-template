"""Defect group controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.service import schema_dump
from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.domain.audit.changes import ChangeRecorder
from app.domain.quality.events import DefectGroupChanged
from app.domain.quality.permissions import DefectPermission
from app.domain.quality.schemas import DefectGroup, DefectGroupCreate, DefectGroupUpdate
from app.domain.quality.services import DefectGroupService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

GroupId = Annotated[
    UUID,
    Parameter(title="Defect group ID", description="The defect group to act on."),
]


_AUDIT_FIELDS = same_fields("name", "description")
"""Fields the ``updated`` audit entries compare."""


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
        defect_groups_service: NamedDependency[DefectGroupService],
        changes: NamedDependency[ChangeRecorder],
        data: DefectGroupCreate,
    ) -> DefectGroup:
        db_obj = await defect_groups_service.create_group(schema_dump(data))
        await changes.record(
            "defect_group.created",
            db_obj,
            event=DefectGroupChanged(group_id=db_obj.id),
        )

        return defect_groups_service.to_schema(db_obj, schema_type=DefectGroup)

    @patch(
        operation_id="UpdateDefectGroup",
        path="/{group_id:uuid}",
        guards=[requires_permission(DefectPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_defect_group(
        self,
        data: DefectGroupUpdate,
        defect_groups_service: NamedDependency[DefectGroupService],
        changes: NamedDependency[ChangeRecorder],
        group_id: GroupId,
    ) -> DefectGroup:
        before = snapshot(await defect_groups_service.get(group_id), _AUDIT_FIELDS)
        db_obj = await defect_groups_service.update_group(
            group_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )

        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await changes.record(
                "defect_group.updated",
                db_obj,
                event=DefectGroupChanged(group_id=db_obj.id),
                details=details,
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
        defect_groups_service: NamedDependency[DefectGroupService],
        changes: NamedDependency[ChangeRecorder],
        group_id: GroupId,
    ) -> DefectGroup:
        return await self._set_archived(defect_groups_service, changes, group_id, archived=True)

    @post(
        operation_id="RestoreDefectGroup",
        path="/{group_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(DefectPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_defect_group(
        self,
        defect_groups_service: NamedDependency[DefectGroupService],
        changes: NamedDependency[ChangeRecorder],
        group_id: GroupId,
    ) -> DefectGroup:
        return await self._set_archived(defect_groups_service, changes, group_id, archived=False)

    @staticmethod
    async def _set_archived(
        defect_groups_service: DefectGroupService,
        changes: ChangeRecorder,
        group_id: UUID,
        *,
        archived: bool,
    ) -> DefectGroup:
        was_archived = (await defect_groups_service.get(group_id)).archived_at is not None
        db_obj = await defect_groups_service.set_archived(group_id, archived=archived)

        if was_archived != archived:
            await changes.record(
                "defect_group.archived" if archived else "defect_group.restored",
                db_obj,
                event=DefectGroupChanged(group_id=db_obj.id),
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
        defect_groups_service: NamedDependency[DefectGroupService],
        changes: NamedDependency[ChangeRecorder],
        group_id: GroupId,
    ) -> None:
        target = await defect_groups_service.delete_group(group_id)
        await changes.record(
            "defect_group.deleted",
            target,
            event=DefectGroupChanged(group_id=target.id),
        )
