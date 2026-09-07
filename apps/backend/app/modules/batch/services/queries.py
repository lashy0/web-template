from __future__ import annotations

from uuid import UUID

from ..exceptions import (
    BatchNotFoundError,
    BatchReceiptNotFoundError,
    BatchShipmentNotFoundError,
)
from ..models import Batch, BatchReceipt, BatchShipment
from ..repositories import (
    BatchReceiptRepository,
    BatchRepository,
    BatchShipmentRepository,
)


async def required_batch(
    repository: BatchRepository,
    batch_id: UUID,
    *,
    for_update: bool = False,
) -> Batch:
    batch = await repository.get_by_id(batch_id, for_update=for_update)

    if batch is None:
        raise BatchNotFoundError

    return batch


async def required_receipt(
    repository: BatchReceiptRepository,
    receipt_id: UUID,
    *,
    batch_id: UUID,
) -> BatchReceipt:
    receipt = await repository.get_by_id(receipt_id)

    if receipt is None or receipt.batch_id != batch_id:
        raise BatchReceiptNotFoundError

    return receipt


async def required_shipment(
    repository: BatchShipmentRepository,
    shipment_id: UUID,
    *,
    batch_id: UUID,
) -> BatchShipment:
    shipment = await repository.get_by_id(shipment_id)

    if shipment is None or shipment.batch_id != batch_id:
        raise BatchShipmentNotFoundError

    return shipment
