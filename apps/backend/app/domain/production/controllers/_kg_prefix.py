"""DevEUI prefix catalog controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.service import schema_dump
from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.domain.audit.changes import ChangeRecorder
from app.domain.production.events import KgPrefixChanged
from app.domain.production.permissions import KgPrefixPermission
from app.domain.production.schemas import (
    KgPrefix,
    KgPrefixCreate,
    KgPrefixUpdate,
)
from app.domain.production.services import KgPrefixService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

PrefixId = Annotated[
    UUID,
    Parameter(title="DevEUI prefix ID", description="The DevEUI prefix to act on."),
]


_AUDIT_FIELDS = same_fields("name")
"""Fields the ``updated`` audit entries compare."""


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
        kg_prefixes_service: NamedDependency[KgPrefixService],
        changes: NamedDependency[ChangeRecorder],
        data: KgPrefixCreate,
    ) -> KgPrefix:
        db_obj = await kg_prefixes_service.create_prefix(schema_dump(data))
        await changes.record(
            "kg_prefix.created",
            db_obj,
            event=KgPrefixChanged(prefix_id=db_obj.id),
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
        data: KgPrefixUpdate,
        kg_prefixes_service: NamedDependency[KgPrefixService],
        changes: NamedDependency[ChangeRecorder],
        prefix_id: PrefixId,
    ) -> KgPrefix:
        before = snapshot(await kg_prefixes_service.get(prefix_id), _AUDIT_FIELDS)
        db_obj = await kg_prefixes_service.update_prefix(
            prefix_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )

        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await changes.record(
                "kg_prefix.updated",
                db_obj,
                event=KgPrefixChanged(prefix_id=db_obj.id),
                details=details,
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
        kg_prefixes_service: NamedDependency[KgPrefixService],
        changes: NamedDependency[ChangeRecorder],
        prefix_id: PrefixId,
    ) -> KgPrefix:
        return await self._set_archived(kg_prefixes_service, changes, prefix_id, archived=True)

    @post(
        operation_id="RestoreKgPrefix",
        path="/{prefix_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(KgPrefixPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_kg_prefix(
        self,
        kg_prefixes_service: NamedDependency[KgPrefixService],
        changes: NamedDependency[ChangeRecorder],
        prefix_id: PrefixId,
    ) -> KgPrefix:
        return await self._set_archived(kg_prefixes_service, changes, prefix_id, archived=False)

    @staticmethod
    async def _set_archived(
        kg_prefixes_service: KgPrefixService,
        changes: ChangeRecorder,
        prefix_id: UUID,
        *,
        archived: bool,
    ) -> KgPrefix:
        was_archived = (await kg_prefixes_service.get(prefix_id)).archived_at is not None
        db_obj = await kg_prefixes_service.set_archived(prefix_id, archived=archived)

        if was_archived != archived:
            await changes.record(
                "kg_prefix.archived" if archived else "kg_prefix.restored",
                db_obj,
                event=KgPrefixChanged(prefix_id=db_obj.id),
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
        kg_prefixes_service: NamedDependency[KgPrefixService],
        changes: NamedDependency[ChangeRecorder],
        prefix_id: PrefixId,
    ) -> None:
        target = await kg_prefixes_service.delete_prefix(prefix_id)
        await changes.record("kg_prefix.deleted", target, event=KgPrefixChanged(prefix_id=target.id))
