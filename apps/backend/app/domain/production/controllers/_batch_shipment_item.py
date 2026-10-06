"""Controllers for the KG units of a batch shipment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from litestar import Controller, Request, delete, get, post
from litestar.di import NamedDependency
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.domain.audit.changes import ChangeRecorder
from app.domain.production.events import BatchChanged
from app.domain.production.permissions import BatchPermission
from app.domain.production.schemas import (
    BatchShipment,
    BatchShipmentItem,
    BatchShipmentUnitsAdd,
    BatchShipmentUnitsAdded,
)
from app.domain.production.services import BatchShipmentItemService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.lorawan import normalize_dev_eui
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

BatchId = Annotated[
    UUID,
    Parameter(title="Batch ID", description="The batch of the shipment."),
]
ShipmentId = Annotated[
    UUID,
    Parameter(title="Shipment ID", description="The shipment the units belong to."),
]
DevEui = Annotated[
    str,
    Parameter(title="DevEUI", description="The KG unit: 16 hexadecimal characters, any case."),
]


class BatchShipmentItemController(Controller):
    """KG units of a batch shipment; they change only while the shipment is open.

    Adding and removing units is not written to the audit log: the shipment's
    completion records what was shipped.
    """

    tags = ["Batch Shipments"]  # noqa: RUF012
    path = "/batches/{batch_id:uuid}/shipments/{shipment_id:uuid}/items"
    dependencies = create_service_dependencies(
        BatchShipmentItemService,
        key="shipment_items_service",
        filters={
            "search": "dev_eui",
            "search_ignore_case": True,
            "pagination_type": "limit_offset",
            "pagination_size": 50,
            "sort_field": "created_at",
            "sort_order": "desc",
        },
    )

    @get(
        operation_id="ListBatchShipmentItems",
        path="",
        guards=[requires_permission(BatchPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def list_items(
        self,
        shipment_items_service: NamedDependency[BatchShipmentItemService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> OffsetPagination[BatchShipmentItem]:
        await shipment_items_service.ensure_shipment_exists(batch_id, shipment_id)
        results, total = await shipment_items_service.get_many_and_count(
            m.BatchShipmentItem.shipment_id == shipment_id,
            *filters,
        )

        return shipment_items_service.to_schema(results, total, filters, schema_type=BatchShipmentItem)

    @post(
        operation_id="AddBatchShipmentUnits",
        path="",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.UPDATE_SHIPMENT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def add_units(
        self,
        request: Request[m.User, Any, Any],
        shipment_items_service: NamedDependency[BatchShipmentItemService],
        changes: NamedDependency[ChangeRecorder],
        data: BatchShipmentUnitsAdd,
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipmentUnitsAdded:
        """Add units by DevEUI or short ID; units that cannot be shipped are listed with the reason."""
        shipment, added, rejected = await shipment_items_service.add_units(
            batch_id,
            shipment_id,
            data.codes,
            added_by_id=request.user.id,
        )
        changes.announce(BatchChanged(batch_id=batch_id))

        return BatchShipmentUnitsAdded(
            added=added,
            rejected=rejected,
            shipment=shipment_items_service.to_schema(shipment, schema_type=BatchShipment),
        )

    @post(
        operation_id="AddPackedBatchShipmentUnits",
        path="/packed",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.UPDATE_SHIPMENT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def add_packed_units(
        self,
        request: Request[m.User, Any, Any],
        shipment_items_service: NamedDependency[BatchShipmentItemService],
        changes: NamedDependency[ChangeRecorder],
        batch_id: BatchId,
        shipment_id: ShipmentId,
    ) -> BatchShipment:
        """Add every packed unit of the batch that is in no other shipment; ``quantity`` shows the result."""
        shipment = await shipment_items_service.add_packed_units(batch_id, shipment_id, added_by_id=request.user.id)
        changes.announce(BatchChanged(batch_id=batch_id))

        return shipment_items_service.to_schema(shipment, schema_type=BatchShipment)

    @delete(
        operation_id="RemoveBatchShipmentUnit",
        path="/{dev_eui:str}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(BatchPermission.UPDATE_SHIPMENT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def remove_unit(
        self,
        shipment_items_service: NamedDependency[BatchShipmentItemService],
        changes: NamedDependency[ChangeRecorder],
        batch_id: BatchId,
        shipment_id: ShipmentId,
        dev_eui: DevEui,
    ) -> None:
        await shipment_items_service.remove_unit(batch_id, shipment_id, normalize_dev_eui(dev_eui))
        changes.announce(BatchChanged(batch_id=batch_id))
