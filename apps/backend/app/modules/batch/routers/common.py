from typing import cast
from uuid import UUID

from fastapi import Request

from app.modules.kg.schemas import KgDevEuiPrefixSummaryResponse, KgVersionSummaryResponse
from app.modules.production_order.schemas import ProductionOrderSummaryResponse
from app.modules.users.models import User
from app.modules.users.schemas import UserSummaryResponse

from ..models import (
    Batch,
    BatchReceipt,
    BatchShipment,
    BatchShipmentItem,
)
from ..schemas import (
    BatchLoRaWanConfigResponse,
    BatchReceiptResponse,
    BatchResponse,
    BatchShipmentItemResponse,
    BatchShipmentResponse,
)
from ..services import BatchManagementService


def _service(request: Request) -> BatchManagementService:
    return cast(BatchManagementService, request.app.state.batch_management)


def _user_response(user: User | None) -> UserSummaryResponse | None:
    return UserSummaryResponse(id=user.id, name=user.name) if user is not None else None


def _batch_response(batch: Batch) -> BatchResponse:
    prefix = batch.kg_dev_eui_prefix
    version = batch.kg_version

    return BatchResponse(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        dev_eui_prefix=KgDevEuiPrefixSummaryResponse(
            prefix=prefix.prefix,
            short_code=prefix.short_code,
            name=prefix.name,
        ),
        kg_version=(
            KgVersionSummaryResponse(
                id=version.id,
                code=version.code,
                name=version.name,
            )
            if version is not None
            else None
        ),
        production_order_id=batch.production_order_id,
        production_order=(
            ProductionOrderSummaryResponse.model_validate(batch.production_order)
            if batch.production_order is not None
            else None
        ),
        planned_qty=batch.planned_qty,
        day_plan_qty=batch.day_plan_qty,
        status=batch.status,
        key_generation_status=batch.key_generation_status,
        lorawan_config=(
            BatchLoRaWanConfigResponse(
                activation_type=batch.lorawan_config.activation_type,
                lorawan_version=batch.lorawan_config.lorawan_version,
                join_eui=batch.lorawan_config.join_eui,
            )
            if batch.lorawan_config is not None
            else None
        ),
        created_by_user_id=batch.created_by_user_id,
        created_by_user=_user_response(batch.created_by_user),
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
        created_by_user=_user_response(receipt.created_by_user),
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
    quantity: int | None = None,
) -> BatchShipmentResponse:
    if quantity is None:
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
        created_by_user=_user_response(shipment.created_by_user),
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
        completed_at=shipment.completed_at,
        voided_at=shipment.voided_at,
        void_reason=shipment.void_reason,
    )
