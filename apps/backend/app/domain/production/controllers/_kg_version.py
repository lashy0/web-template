"""KG version catalog controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.service import schema_dump
from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.domain.audit.changes import ChangeRecorder
from app.domain.production.events import KgVersionChanged
from app.domain.production.permissions import KgVersionPermission
from app.domain.production.schemas import (
    KgVersion,
    KgVersionCreate,
    KgVersionUpdate,
)
from app.domain.production.services import KgVersionService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

VersionId = Annotated[
    UUID,
    Parameter(title="KG version ID", description="The KG version to act on."),
]


_AUDIT_FIELDS = same_fields("name", "description")
"""Fields the ``updated`` audit entries compare."""


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
        kg_versions_service: NamedDependency[KgVersionService],
        changes: NamedDependency[ChangeRecorder],
        data: KgVersionCreate,
    ) -> KgVersion:
        db_obj = await kg_versions_service.create_version(schema_dump(data))
        await changes.record(
            "kg_version.created",
            db_obj,
            event=KgVersionChanged(version_id=db_obj.id),
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
        data: KgVersionUpdate,
        kg_versions_service: NamedDependency[KgVersionService],
        changes: NamedDependency[ChangeRecorder],
        version_id: VersionId,
    ) -> KgVersion:
        before = snapshot(await kg_versions_service.get(version_id), _AUDIT_FIELDS)
        db_obj = await kg_versions_service.update_version(
            version_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )
        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await changes.record(
                "kg_version.updated",
                db_obj,
                event=KgVersionChanged(version_id=db_obj.id),
                details=details,
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
        kg_versions_service: NamedDependency[KgVersionService],
        changes: NamedDependency[ChangeRecorder],
        version_id: VersionId,
    ) -> KgVersion:
        return await self._set_archived(kg_versions_service, changes, version_id, archived=True)

    @post(
        operation_id="RestoreKgVersion",
        path="/{version_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(KgVersionPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_kg_version(
        self,
        kg_versions_service: NamedDependency[KgVersionService],
        changes: NamedDependency[ChangeRecorder],
        version_id: VersionId,
    ) -> KgVersion:
        return await self._set_archived(kg_versions_service, changes, version_id, archived=False)

    @staticmethod
    async def _set_archived(
        kg_versions_service: KgVersionService,
        changes: ChangeRecorder,
        version_id: UUID,
        *,
        archived: bool,
    ) -> KgVersion:
        was_archived = (await kg_versions_service.get(version_id)).archived_at is not None
        db_obj = await kg_versions_service.set_archived(version_id, archived=archived)

        if was_archived != archived:
            await changes.record(
                "kg_version.archived" if archived else "kg_version.restored",
                db_obj,
                event=KgVersionChanged(version_id=db_obj.id),
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
        kg_versions_service: NamedDependency[KgVersionService],
        changes: NamedDependency[ChangeRecorder],
        version_id: VersionId,
    ) -> None:
        target = await kg_versions_service.delete_version(version_id)
        await changes.record(
            "kg_version.deleted",
            target,
            event=KgVersionChanged(version_id=target.id),
        )
