"""Multicast group catalog controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from advanced_alchemy.service import schema_dump
from litestar import Controller, delete, get, patch, post
from litestar.datastructures import CacheControlHeader
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.domain.audit.changes import ChangeRecorder
from app.domain.production.events import MulticastGroupChanged
from app.domain.production.permissions import MulticastGroupPermission
from app.domain.production.schemas import (
    MulticastGroup,
    MulticastGroupCreate,
    MulticastGroupKeys,
    MulticastGroupUpdate,
)
from app.domain.production.services import MulticastGroupService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

MulticastGroupId = Annotated[
    UUID,
    Parameter(title="Multicast group ID", description="The multicast group to act on."),
]


_AUDIT_FIELDS = same_fields("name", "group_id", "frequency_hz", "datarate")
"""Fields the ``updated`` audit entries compare."""


class MulticastGroupController(Controller):
    """Multicast groups that KG units of batches are provisioned with."""

    tags = ["KG catalogs"]  # noqa: RUF012
    path = "/kg/multicast-groups"
    dependencies = create_service_dependencies(
        MulticastGroupService,
        key="multicast_groups_service",
        filters={
            "id_filter": UUID,
            "search": "name,mc_addr",
            "search_ignore_case": True,
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "name",
            "sort_order": "asc",
            "in_fields": [FieldNameType(name="group_id", type_hint=int)],
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)

    @get(
        operation_id="ListMulticastGroups",
        guards=[requires_permission(MulticastGroupPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_multicast_groups(
        self,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[MulticastGroup]:
        results, total = await multicast_groups_service.get_many_and_count(*filters, *archived_filter)

        return multicast_groups_service.to_schema(results, total, filters, schema_type=MulticastGroup)

    @get(
        operation_id="GetMulticastGroup",
        path="/{multicast_group_id:uuid}",
        guards=[requires_permission(MulticastGroupPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_multicast_group(
        self,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        multicast_group_id: MulticastGroupId,
    ) -> MulticastGroup:
        db_obj = await multicast_groups_service.get(multicast_group_id)

        return multicast_groups_service.to_schema(db_obj, schema_type=MulticastGroup)

    @get(
        operation_id="GetMulticastGroupKeys",
        path="/{multicast_group_id:uuid}/keys",
        guards=[requires_permission(MulticastGroupPermission.READ_KEYS)],
        responses=error_responses(401, 403, 404),
        # The keys must not stay in a browser or proxy cache.
        cache_control=CacheControlHeader(no_store=True),
    )
    async def get_multicast_group_keys(
        self,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        multicast_group_id: MulticastGroupId,
    ) -> MulticastGroupKeys:
        """The McKey of the group and its session keys; see ``docs/domain/multicast.md``."""
        return await multicast_groups_service.get_keys(multicast_group_id)

    @post(
        operation_id="CreateMulticastGroup",
        path="",
        guards=[requires_permission(MulticastGroupPermission.CREATE)],
        responses=error_responses(401, 403, 409),
    )
    async def create_multicast_group(
        self,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        changes: NamedDependency[ChangeRecorder],
        data: MulticastGroupCreate,
    ) -> MulticastGroup:
        db_obj = await multicast_groups_service.create_group(schema_dump(data))
        await changes.record(
            "multicast_group.created",
            db_obj,
            event=MulticastGroupChanged(multicast_group_id=db_obj.id),
            details={"group_id": db_obj.group_id, "mc_addr": db_obj.mc_addr},
        )

        return multicast_groups_service.to_schema(db_obj, schema_type=MulticastGroup)

    @patch(
        operation_id="UpdateMulticastGroup",
        path="/{multicast_group_id:uuid}",
        guards=[requires_permission(MulticastGroupPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_multicast_group(
        self,
        data: MulticastGroupUpdate,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        changes: NamedDependency[ChangeRecorder],
        multicast_group_id: MulticastGroupId,
    ) -> MulticastGroup:
        before = snapshot(await multicast_groups_service.get(multicast_group_id), _AUDIT_FIELDS)
        db_obj = await multicast_groups_service.update_group(
            multicast_group_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )

        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await changes.record(
                "multicast_group.updated",
                db_obj,
                event=MulticastGroupChanged(multicast_group_id=db_obj.id),
                details=details,
            )

        return multicast_groups_service.to_schema(db_obj, schema_type=MulticastGroup)

    @post(
        operation_id="ArchiveMulticastGroup",
        path="/{multicast_group_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(MulticastGroupPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def archive_multicast_group(
        self,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        changes: NamedDependency[ChangeRecorder],
        multicast_group_id: MulticastGroupId,
    ) -> MulticastGroup:
        return await self._set_archived(multicast_groups_service, changes, multicast_group_id, archived=True)

    @post(
        operation_id="RestoreMulticastGroup",
        path="/{multicast_group_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(MulticastGroupPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_multicast_group(
        self,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        changes: NamedDependency[ChangeRecorder],
        multicast_group_id: MulticastGroupId,
    ) -> MulticastGroup:
        return await self._set_archived(multicast_groups_service, changes, multicast_group_id, archived=False)

    @staticmethod
    async def _set_archived(
        multicast_groups_service: MulticastGroupService,
        changes: ChangeRecorder,
        multicast_group_id: UUID,
        *,
        archived: bool,
    ) -> MulticastGroup:
        was_archived = (await multicast_groups_service.get(multicast_group_id)).archived_at is not None
        db_obj = await multicast_groups_service.set_archived(multicast_group_id, archived=archived)

        if was_archived != archived:
            await changes.record(
                "multicast_group.archived" if archived else "multicast_group.restored",
                db_obj,
                event=MulticastGroupChanged(multicast_group_id=db_obj.id),
            )

        return multicast_groups_service.to_schema(db_obj, schema_type=MulticastGroup)

    @delete(
        operation_id="DeleteMulticastGroup",
        path="/{multicast_group_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(MulticastGroupPermission.DELETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def delete_multicast_group(
        self,
        multicast_groups_service: NamedDependency[MulticastGroupService],
        changes: NamedDependency[ChangeRecorder],
        multicast_group_id: MulticastGroupId,
    ) -> None:
        target = await multicast_groups_service.delete_group(multicast_group_id)
        await changes.record(
            "multicast_group.deleted",
            target,
            event=MulticastGroupChanged(multicast_group_id=target.id),
            details={"group_id": target.group_id, "mc_addr": target.mc_addr},
        )
