from typing import cast
from uuid import UUID

from fastapi import Request

from ..models import (
    Batch,
    BatchReceipt,
    BatchShipment,
    BatchShipmentItem,
)
from ..schemas import (
    BatchReceiptResponse,
    BatchResponse,
    BatchShipmentItemResponse,
    BatchShipmentResponse,
)
from ..services import BatchManagementService


def _service(request: Request) -> BatchManagementService:
    return cast(BatchManagementService, request.app.state.batch_management)


def _batch_response(batch: Batch) -> BatchResponse:
    return BatchResponse(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        dev_eui_prefix=batch.dev_eui_prefix,
        planned_qty=batch.planned_qty,
        day_plan_qty=batch.day_plan_qty,
        status=batch.status,
        created_by_user_id=batch.created_by_user_id,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        completed_at=batch.completed_at,
        archived_at=batch.archived_at,
    )


def _receipt_response(receipt: BatchReceipt) -> BatchReceiptResponse:
    return BatchReceiptResponse(
        id=receipt.id,
        batch_id=receipt.batch_id,
        quantity=receipt.quantity,
        comment=receipt.comment,
        created_by_user_id=receipt.created_by_user_id,
        created_at=receipt.created_at,
        updated_at=receipt.updated_at,
        voided_at=receipt.voided_at,
        void_reason=receipt.void_reason,
    )


def _shipment_item_response(item: BatchShipmentItem) -> BatchShipmentItemResponse:
    return BatchShipmentItemResponse(
        shipment_id=item.shipment_id,
        kg_dev_eui=item.kg_dev_eui,
        created_at=item.created_at,
    )


async def _shipment_response(
    request: Request,
    *,
    batch_id: UUID,
    shipment: BatchShipment,
) -> BatchShipmentResponse:
    quantity = await _service(request).count_shipment_items(
        batch_id=batch_id,
        shipment_id=shipment.id,
    )

    return BatchShipmentResponse(
        id=shipment.id,
        batch_id=shipment.batch_id,
        comment=shipment.comment,
        quantity=quantity,
        created_by_user_id=shipment.created_by_user_id,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
        completed_at=shipment.completed_at,
        voided_at=shipment.voided_at,
        void_reason=shipment.void_reason,
    )
