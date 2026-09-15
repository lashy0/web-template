from __future__ import annotations

from uuid import UUID

from app.domains.production.batches.model import Batch
from app.domains.production.batches.repository import BatchRepository
from app.domains.production.exceptions import BatchNotFoundError, BatchShipmentNotFoundError

from .model import BatchShipment, BatchShipmentItem
from .repository import ShipmentRepository


class ShipmentQueries:
    def __init__(self, batches: BatchRepository, shipments: ShipmentRepository) -> None:
        self._batches = batches
        self._shipments = shipments

    async def list_by_batch(
        self, batch_id: UUID, *, include_voided: bool = False
    ) -> list[BatchShipment]:
        await self.required_batch(batch_id)
        return await self._shipments.list_by_batch(batch_id, include_voided=include_voided)

    async def list_items(self, *, batch_id: UUID, shipment_id: UUID) -> list[BatchShipmentItem]:
        shipment = await self.required_shipment(shipment_id, batch_id=batch_id)
        return await self._shipments.list_items(shipment.id)

    async def item_counts(self, batch_id: UUID) -> dict[UUID, int]:
        await self.required_batch(batch_id)
        return await self._shipments.item_counts_by_batch(batch_id)

    async def item_count(self, *, batch_id: UUID, shipment_id: UUID) -> int:
        shipment = await self.required_shipment(shipment_id, batch_id=batch_id)
        return await self._shipments.item_count(shipment.id)

    async def shipped_total(self, batch_id: UUID) -> int:
        await self.required_batch(batch_id)
        return await self._shipments.shipped_total(batch_id)

    async def required_batch(self, batch_id: UUID, *, for_update: bool = False) -> Batch:
        batch = await self._batches.get(batch_id, for_update=for_update)
        if batch is None:
            raise BatchNotFoundError
        return batch

    async def required_shipment(
        self, shipment_id: UUID, *, batch_id: UUID, for_update: bool = False
    ) -> BatchShipment:
        shipment = await self._shipments.get(shipment_id, for_update=for_update)
        if shipment is None or shipment.batch_id != batch_id:
            raise BatchShipmentNotFoundError
        return shipment
