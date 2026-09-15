"""Response mapping for the production batch HTTP adapters."""

from app.domains.identity.users.schemas import UserSummaryResponse
from app.domains.production.kg.schemas import (
    KgDevEuiPrefixSummaryResponse,
    KgVersionSummaryResponse,
)
from app.domains.production.preparation.model import (
    BatchKeyGenerationJob,
    BatchKeyGenerationStatus,
)
from app.domains.production.production_orders.schemas import ProductionOrderSummaryResponse
from app.domains.production.receipts.model import BatchReceipt
from app.domains.production.receipts.schemas import BatchReceiptResponse
from app.domains.production.shipments.model import BatchShipment, BatchShipmentItem
from app.domains.production.shipments.schemas import (
    BatchShipmentItemResponse,
    BatchShipmentResponse,
)

from .model import Batch
from .schemas import BatchLoRaWanConfigResponse, BatchResponse


def user_response(user: object | None) -> UserSummaryResponse | None:
    return (
        UserSummaryResponse(id=user.id, name=user.name)  # type: ignore[attr-defined]
        if user is not None
        else None
    )


def batch_response(
    batch: Batch,
    *,
    can_delete: bool,
    job: BatchKeyGenerationJob | None,
) -> BatchResponse:
    prefix = batch.kg_dev_eui_prefix
    version = batch.kg_version
    return BatchResponse(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        dev_eui_prefix=KgDevEuiPrefixSummaryResponse(
            prefix=prefix.prefix, short_code=prefix.short_code, name=prefix.name
        ),
        kg_version=(
            KgVersionSummaryResponse(id=version.id, code=version.code, name=version.name)
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
        preparation_status=job.status if job is not None else BatchKeyGenerationStatus.READY,
        preparation_progress=job.progress if job is not None else 100,
        preparation_error_code=job.error_code if job is not None else None,
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
        created_by_user=user_response(batch.created_by_user),
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        completed_at=batch.completed_at,
        archived_at=batch.archived_at,
        can_delete=can_delete,
    )


def receipt_response(receipt: BatchReceipt) -> BatchReceiptResponse:
    return BatchReceiptResponse(
        id=receipt.id,
        batch_id=receipt.batch_id,
        quantity=receipt.quantity,
        comment=receipt.comment,
        created_by_user_id=receipt.created_by_user_id,
        created_by_user=user_response(receipt.created_by_user),
        created_at=receipt.created_at,
        updated_at=receipt.updated_at,
        voided_at=receipt.voided_at,
        void_reason=receipt.void_reason,
    )


def shipment_item_response(item: BatchShipmentItem) -> BatchShipmentItemResponse:
    return BatchShipmentItemResponse(
        shipment_id=item.shipment_id, kg_dev_eui=item.kg_dev_eui, created_at=item.created_at
    )


def shipment_response(shipment: BatchShipment, *, quantity: int) -> BatchShipmentResponse:
    return BatchShipmentResponse(
        id=shipment.id,
        batch_id=shipment.batch_id,
        comment=shipment.comment,
        quantity=quantity,
        created_by_user_id=shipment.created_by_user_id,
        created_by_user=user_response(shipment.created_by_user),
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
        completed_at=shipment.completed_at,
        voided_at=shipment.voided_at,
        void_reason=shipment.void_reason,
    )
