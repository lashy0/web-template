"""Shipment controllers nested under their batch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, Request, get, patch, post
from litestar.di import NamedDependency
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK

from app.db import models as m
from app.db.enums import BatchShipmentStatus
from app.domain.audit.changes import ChangeRecorder
from app.domain.production.events import BatchChanged
from app.domain.production.permissions import BatchPermission
from app.domain.production.schemas import (
    BatchShipment,
    BatchShipmentComplete,
    BatchShipmentCreate,
    BatchShipmentUpdate,
    BatchShipmentVoid,
)
from app.domain.production.services import BatchShipmentService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.openapi import error_responses

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


_AUDIT_FIELDS = same_fields("comment")
"""Fields the ``updated`` audit entries compare."""


class BatchShipmentController(Controller):
    """Shipments of packed KG units of a batch; the units are under ``.../{shipmentId}/items``."""

    tags = ["Batch Shipments"]  # noqa: RUF012
    path = "/batches/{batch_id:uuid}/shipments"
    dependencies = create_service_dependencies(
        BatchShipmentService,
        key="shipments_service",
        filters={
            "search": "comment",
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

    @staticmethod
    async def _record_shipment_change(
        changes: ChangeRecorder,
        action: str,
        shipment: m.BatchShipment,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a change of the shipment; its entry names the batch, whose page shows the shipment."""
        await changes.record(
            action,
            shipment,
            event=BatchChanged(batch_id=shipment.batch_id),
            details={"batch_id": str(shipment.batch_id), **(details or {})},
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
        changes: NamedDependency[ChangeRecorder],
        data: BatchShipmentCreate,
        batch_id: BatchId,
    ) -> BatchShipment:
        db_obj = await shipments_service.create_shipment(
            batch_id,
            data,
            created_by_id=request.user.id,
        )
        await self._record_shipment_change(
            changes,
            "batch_shipment.created",
            db_obj,
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
        shipments_service: NamedDependency[BatchShipmentService],
        changes: NamedDependency[ChangeRecorder],
        data: BatchShipmentUpdate,
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        before = snapshot(await shipments_service.get(shipment_id), _AUDIT_FIELDS)
        db_obj = await shipments_service.update_shipment(
            batch_id,
            shipment_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )

        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await self._record_shipment_change(
                changes,
                "batch_shipment.updated",
                db_obj,
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
        changes: NamedDependency[ChangeRecorder],
        data: BatchShipmentComplete,
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        """Ship the units; ``batch_shipment_quantity_changed`` when the shipment no longer holds ``expectedQuantity``."""
        db_obj = await shipments_service.complete_shipment(
            batch_id,
            shipment_id,
            completed_by_id=request.user.id,
            expected_quantity=data.expected_quantity,
        )
        await self._record_shipment_change(
            changes,
            "batch_shipment.completed",
            db_obj,
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
        changes: NamedDependency[ChangeRecorder],
        data: BatchShipmentVoid,
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        db_obj = await shipments_service.void_shipment(
            batch_id,
            shipment_id,
            data.reason,
            voided_by_id=request.user.id,
        )
        await self._record_shipment_change(
            changes,
            "batch_shipment.voided",
            db_obj,
            details={
                "quantity": db_obj.quantity,
                "was_completed": db_obj.completed_at is not None,
                "reason": data.reason,
            },
        )

        return shipments_service.to_schema(db_obj, schema_type=BatchShipment)
