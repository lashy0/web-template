"""Production batch controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import msgspec
from advanced_alchemy.extensions.litestar.providers import FieldNameType
from advanced_alchemy.filters import FilterTypes, NotNullFilter, NullFilter
from litestar import Controller, Request, delete, get, patch, post, put
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, QueryParameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.db.enums import BatchStatus
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.production.permissions import BatchPermission
from app.domain.production.schemas import (
    Batch,
    BatchCreate,
    BatchProductionOrderAssignment,
    BatchUpdate,
    DevEuiRange,
)
from app.domain.production.schemas._batch import PlannedQty
from app.domain.production.services import BatchService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.service.pagination import OffsetPagination

BatchId = Annotated[
    UUID,
    Parameter(title="Batch ID", description="The batch to act on."),
]


def provide_production_order_presence_filter(
    has_production_order: Annotated[
        bool | None,
        QueryParameter(
            name="hasProductionOrder",
            description="Only batches with (true) or without (false) a production order; all when omitted.",
        ),
    ] = None,
) -> list[FilterTypes]:
    if has_production_order is None:
        return []

    return [NotNullFilter("production_order_id") if has_production_order else NullFilter("production_order_id")]


class BatchController(Controller):
    """Production batches."""

    tags = ["Batches"]  # noqa: RUF012
    path = "/batches"
    dependencies = create_service_dependencies(
        BatchService,
        key="batches_service",
        filters={
            "id_filter": UUID,
            "search": "name,description",
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
            "in_fields": [
                FieldNameType(name="status", type_hint=BatchStatus),
                FieldNameType(name="production_order_id", type_hint=UUID),
            ],
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["production_order_presence_filter"] = Provide(
        provide_production_order_presence_filter,
        sync_to_thread=False,
    )
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_batch_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.Batch,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="batch",
            target_id=str(target.id),
            target_label=target.name,
            details=details,
            request=request,
        )

    @get(
        operation_id="ListBatches",
        guards=[requires_permission(BatchPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_batches(
        self,
        batches_service: NamedDependency[BatchService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
        production_order_presence_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[Batch]:
        results, total = await batches_service.get_many_and_count(
            *filters,
            *archived_filter,
            *production_order_presence_filter,
        )

        return batches_service.to_schema(results, total, filters, schema_type=Batch)

    @get(
        operation_id="PreviewBatchDevEuiRange",
        path="/dev-eui-range-preview",
        guards=[requires_permission(BatchPermission.CREATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def preview_dev_eui_range(
        self,
        batches_service: NamedDependency[BatchService],
        kg_prefix_id: Annotated[
            UUID,
            QueryParameter(name="kgPrefixId", description="The prefix to allocate from."),
        ],
        planned_qty: Annotated[PlannedQty, QueryParameter(name="plannedQty")],
    ) -> DevEuiRange:
        """Show the DevEUI range a new batch would get now; another batch may take it first."""
        first_dev_eui, last_dev_eui = await batches_service.preview_dev_eui_range(kg_prefix_id, planned_qty)

        return DevEuiRange(first_dev_eui=first_dev_eui, last_dev_eui=last_dev_eui)

    @get(
        operation_id="GetBatch",
        path="/{batch_id:uuid}",
        guards=[requires_permission(BatchPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_batch(
        self,
        batches_service: NamedDependency[BatchService],
        batch_id: BatchId,
    ) -> Batch:
        db_obj = await batches_service.get(batch_id)

        return batches_service.to_schema(db_obj, schema_type=Batch)

    @post(
        operation_id="CreateBatch",
        path="",
        guards=[requires_permission(BatchPermission.CREATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def create_batch(
        self,
        request: Request[m.User, Any, Any],
        batches_service: NamedDependency[BatchService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: BatchCreate,
    ) -> Batch:
        db_obj = await batches_service.create_batch(data, created_by_id=request.user.id)
        await self._log_batch_action(
            request,
            audit_service,
            action="batch.created",
            target=db_obj,
            details={
                "planned_qty": db_obj.planned_qty,
                "first_dev_eui": db_obj.first_dev_eui,
                "last_dev_eui": db_obj.last_dev_eui,
            },
        )

        return batches_service.to_schema(db_obj, schema_type=Batch)

    @patch(
        operation_id="UpdateBatch",
        path="/{batch_id:uuid}",
        guards=[requires_permission(BatchPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_batch(
        self,
        request: Request[m.User, Any, Any],
        data: BatchUpdate,
        batches_service: NamedDependency[BatchService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        batch_id: BatchId,
    ) -> Batch:
        db_obj = await batches_service.update_batch(batch_id, data.to_dict())
        await self._log_batch_action(
            request,
            audit_service,
            action="batch.updated",
            target=db_obj,
            details={
                "fields": [
                    field
                    for field in ("name", "description", "day_plan_qty")
                    if getattr(data, field) is not msgspec.UNSET
                ]
            },
        )

        return batches_service.to_schema(db_obj, schema_type=Batch)

    @put(
        operation_id="AssignBatchProductionOrder",
        path="/{batch_id:uuid}/production-order",
        guards=[requires_permission(BatchPermission.ASSIGN_PRODUCTION_ORDER)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def assign_production_order(
        self,
        request: Request[m.User, Any, Any],
        data: BatchProductionOrderAssignment,
        batches_service: NamedDependency[BatchService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        batch_id: BatchId,
    ) -> Batch:
        previous_order_id = (await batches_service.get(batch_id)).production_order_id
        db_obj = await batches_service.assign_production_order(batch_id, data.production_order_id)

        if previous_order_id != data.production_order_id:
            await self._log_batch_action(
                request,
                audit_service,
                action="batch.production_order_changed",
                target=db_obj,
                details={
                    "from": str(previous_order_id) if previous_order_id else None,
                    "to": str(data.production_order_id) if data.production_order_id else None,
                },
            )

        return batches_service.to_schema(db_obj, schema_type=Batch)

    @post(
        operation_id="CompleteBatch",
        path="/{batch_id:uuid}/complete",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.COMPLETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def complete_batch(
        self,
        request: Request[m.User, Any, Any],
        batches_service: NamedDependency[BatchService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        batch_id: BatchId,
    ) -> Batch:
        db_obj = await batches_service.complete_batch(batch_id)
        await self._log_batch_action(request, audit_service, action="batch.completed", target=db_obj)

        return batches_service.to_schema(db_obj, schema_type=Batch)

    @post(
        operation_id="ArchiveBatch",
        path="/{batch_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def archive_batch(
        self,
        request: Request[m.User, Any, Any],
        batches_service: NamedDependency[BatchService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        batch_id: BatchId,
    ) -> Batch:
        return await self._set_archived(request, batches_service, audit_service, batch_id, archived=True)

    @post(
        operation_id="RestoreBatch",
        path="/{batch_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_batch(
        self,
        request: Request[m.User, Any, Any],
        batches_service: NamedDependency[BatchService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        batch_id: BatchId,
    ) -> Batch:
        return await self._set_archived(request, batches_service, audit_service, batch_id, archived=False)

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        batches_service: BatchService,
        audit_service: AuditLogService,
        batch_id: UUID,
        *,
        archived: bool,
    ) -> Batch:
        was_archived = (await batches_service.get(batch_id)).archived_at is not None
        db_obj = await batches_service.set_archived(batch_id, archived=archived)

        if was_archived != archived:
            await self._log_batch_action(
                request,
                audit_service,
                action="batch.archived" if archived else "batch.restored",
                target=db_obj,
            )

        return batches_service.to_schema(db_obj, schema_type=Batch)

    @delete(
        operation_id="DeleteBatch",
        path="/{batch_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(BatchPermission.DELETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def delete_batch(
        self,
        request: Request[m.User, Any, Any],
        batches_service: NamedDependency[BatchService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        batch_id: BatchId,
    ) -> None:
        target = await batches_service.delete_batch(batch_id)
        await self._log_batch_action(
            request,
            audit_service,
            action="batch.deleted",
            target=target,
            details={"first_dev_eui": target.first_dev_eui, "last_dev_eui": target.last_dev_eui},
        )
