"""Shipment controllers nested under their batch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, Request, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK

from app.db import models as m
from app.db.enums import BatchShipmentStatus
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.production.permissions import BatchPermission
from app.domain.production.schemas import (
    BatchShipment,
    BatchShipmentCreate,
    BatchShipmentUpdate,
    BatchShipmentVoid,
)
from app.domain.production.services import BatchShipmentService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

BatchId = Annotated[
    UUID,
    Parameter(title="Batch ID", description="The batch the shipments belong to."),
]
ShipmentId = Annotated[
    UUID,
    Parameter(title="Shipment ID", description="The shipment to act on."),
]


_AUDIT_FIELDS = same_fields("recipient", "waybill_number", "comment")
"""Fields the ``updated`` audit entries compare."""


class BatchShipmentController(Controller):
    """Shipments of packed KG units of a batch; the units are under ``.../{shipmentId}/items``."""

    tags = ["Batch Shipments"]  # noqa: RUF012
    path = "/batches/{batch_id:uuid}/shipments"
    dependencies = create_service_dependencies(
        BatchShipmentService,
        key="shipments_service",
        filters={
            "search": "recipient,waybill_number,comment",
            "search_ignore_case": True,
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
            "in_fields": [
                FieldNameType(name="status", type_hint=BatchShipmentStatus),
            ],
        },
    )
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_shipment_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.BatchShipment,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="batch_shipment",
            target_id=str(target.id),
            target_label=str(target.number),
            details={"batch_id": str(target.batch_id), **(details or {})},
            request=request,
        )

    @get(
        operation_id="ListBatchShipments",
        path="",
        guards=[requires_permission(BatchPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def list_shipments(
        self,
        shipments_service: NamedDependency[BatchShipmentService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        batch_id: BatchId,
    ) -> OffsetPagination[BatchShipment]:
        await shipments_service.ensure_batch_exists(batch_id)
        results, total = await shipments_service.get_many_and_count(
            m.BatchShipment.batch_id == batch_id,
            *filters,
        )

        return shipments_service.to_schema(results, total, filters, schema_type=BatchShipment)

    @get(
        operation_id="GetBatchShipment",
        path="/{shipment_id:uuid}",
        guards=[requires_permission(BatchPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_shipment(
        self,
        shipments_service: NamedDependency[BatchShipmentService],
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        db_obj = await shipments_service.get_shipment(batch_id, shipment_id)

        return shipments_service.to_schema(db_obj, schema_type=BatchShipment)

    @post(
        operation_id="CreateBatchShipment",
        path="",
        guards=[requires_permission(BatchPermission.CREATE_SHIPMENT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def create_shipment(
        self,
        request: Request[m.User, Any, Any],
        shipments_service: NamedDependency[BatchShipmentService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: BatchShipmentCreate,
        batch_id: BatchId,
    ) -> BatchShipment:
        db_obj = await shipments_service.create_shipment(
            batch_id,
            data,
            created_by_id=request.user.id,
        )
        await self._log_shipment_action(
            request,
            audit_service,
            action="batch_shipment.created",
            target=db_obj,
        )

        return shipments_service.to_schema(db_obj, schema_type=BatchShipment)

    @patch(
        operation_id="UpdateBatchShipment",
        path="/{shipment_id:uuid}",
        guards=[requires_permission(BatchPermission.UPDATE_SHIPMENT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_shipment(
        self,
        request: Request[m.User, Any, Any],
        shipments_service: NamedDependency[BatchShipmentService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: BatchShipmentUpdate,
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        before = snapshot(await shipments_service.get(shipment_id), _AUDIT_FIELDS)
        db_obj = await shipments_service.update_shipment(batch_id, shipment_id, data.to_dict())
        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await self._log_shipment_action(
                request,
                audit_service,
                action="batch_shipment.updated",
                target=db_obj,
                details=details,
            )

        return shipments_service.to_schema(db_obj, schema_type=BatchShipment)

    @post(
        operation_id="CompleteBatchShipment",
        path="/{shipment_id:uuid}/complete",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.COMPLETE_SHIPMENT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def complete_shipment(
        self,
        request: Request[m.User, Any, Any],
        shipments_service: NamedDependency[BatchShipmentService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        db_obj = await shipments_service.complete_shipment(batch_id, shipment_id)
        await self._log_shipment_action(
            request,
            audit_service,
            action="batch_shipment.completed",
            target=db_obj,
            details={"quantity": db_obj.quantity},
        )

        return shipments_service.to_schema(db_obj, schema_type=BatchShipment)

    @post(
        operation_id="VoidBatchShipment",
        path="/{shipment_id:uuid}/void",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.VOID_SHIPMENT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def void_shipment(
        self,
        request: Request[m.User, Any, Any],
        shipments_service: NamedDependency[BatchShipmentService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: BatchShipmentVoid,
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        db_obj = await shipments_service.void_shipment(batch_id, shipment_id, data.reason)
        await self._log_shipment_action(
            request,
            audit_service,
            action="batch_shipment.voided",
            target=db_obj,
            details={
                "quantity": db_obj.quantity,
                "was_completed": db_obj.completed_at is not None,
                "reason": data.reason,
            },
        )

        return shipments_service.to_schema(db_obj, schema_type=BatchShipment)
