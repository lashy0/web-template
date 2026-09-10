from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.modules.lorawan.domain import ActivationType, LoRaWanVersion

from ..models import (
    Batch,
    BatchReceipt,
    BatchShipment,
    BatchShipmentItem,
    BatchStatus,
)
from .batch import BatchService
from .lifecycle import BATCH_EDIT_WINDOW
from .receipt import ReceiptService
from .shipment import ShipmentService


class BatchManagementService:
    """Compatibility facade; new callers can use the three focused services."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self.batch = BatchService(session_factory, edit_window=edit_window)
        self.receipt = ReceiptService(session_factory, edit_window=edit_window)
        self.shipment = ShipmentService(session_factory, edit_window=edit_window)

    async def get(self, batch_id: UUID) -> Batch | None:
        return await self.batch.get(batch_id)

    async def list(
        self,
        *,
        q: str | None,
        status: BatchStatus | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
        production_order_id: UUID | None = None,
        without_production_order: bool = False,
    ) -> tuple[list[Batch], int]:
        return await self.batch.list(
            q=q,
            status=status,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            production_order_id=production_order_id,
            without_production_order=without_production_order,
        )

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
        activation_type: ActivationType,
        lorawan_version: LoRaWanVersion,
        kg_version_id: UUID | None = None,
        production_order_id: UUID | None = None,
    ) -> Batch:
        return await self.batch.create(
            actor=actor,
            name=name,
            description=description,
            dev_eui_prefix=dev_eui_prefix,
            planned_qty=planned_qty,
            day_plan_qty=day_plan_qty,
            activation_type=activation_type,
            lorawan_version=lorawan_version,
            kg_version_id=kg_version_id,
            production_order_id=production_order_id,
        )

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        updates: Mapping[str, object],
    ) -> Batch:
        return await self.batch.update(
            actor=actor,
            batch_id=batch_id,
            updates=updates,
        )

    async def assign_production_order(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        production_order_id: UUID | None,
    ) -> Batch:
        return await self.batch.assign_production_order(
            actor=actor,
            batch_id=batch_id,
            production_order_id=production_order_id,
        )

    async def complete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> Batch:
        return await self.batch.complete(
            actor=actor,
            batch_id=batch_id,
        )

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        archived: bool,
    ) -> Batch:
        return await self.batch.set_archived(
            actor=actor,
            batch_id=batch_id,
            archived=archived,
        )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> None:
        return await self.batch.delete(
            actor=actor,
            batch_id=batch_id,
        )

    async def list_receipts(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchReceipt]:
        return await self.receipt.list_receipts(
            batch_id,
            include_voided=include_voided,
        )

    async def get_received_total(self, batch_id: UUID) -> int:
        return await self.receipt.get_received_total(batch_id)

    async def create_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        quantity: int,
        comment: str | None,
    ) -> BatchReceipt:
        return await self.receipt.create_receipt(
            actor=actor,
            batch_id=batch_id,
            quantity=quantity,
            comment=comment,
        )

    async def update_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchReceipt:
        return await self.receipt.update_receipt(
            actor=actor,
            batch_id=batch_id,
            receipt_id=receipt_id,
            updates=updates,
        )

    async def void_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        reason: str,
    ) -> BatchReceipt:
        return await self.receipt.void_receipt(
            actor=actor,
            batch_id=batch_id,
            receipt_id=receipt_id,
            reason=reason,
        )

    async def list_shipments(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchShipment]:
        return await self.shipment.list_shipments(
            batch_id,
            include_voided=include_voided,
        )

    async def get_shipped_total(self, batch_id: UUID) -> int:
        return await self.shipment.get_shipped_total(batch_id)

    async def create_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        comment: str | None,
    ) -> BatchShipment:
        return await self.shipment.create_shipment(
            actor=actor,
            batch_id=batch_id,
            comment=comment,
        )

    async def update_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchShipment:
        return await self.shipment.update_shipment(
            actor=actor,
            batch_id=batch_id,
            shipment_id=shipment_id,
            updates=updates,
        )

    async def list_shipment_items(
        self,
        *,
        batch_id: UUID,
        shipment_id: UUID,
    ) -> list[BatchShipmentItem]:
        return await self.shipment.list_shipment_items(
            batch_id=batch_id,
            shipment_id=shipment_id,
        )

    async def count_shipment_quantities(self, batch_id: UUID) -> dict[UUID, int]:
        return await self.shipment.count_shipment_quantities(batch_id)

    async def count_shipment_items(
        self,
        *,
        batch_id: UUID,
        shipment_id: UUID,
    ) -> int:
        return await self.shipment.count_shipment_items(
            batch_id=batch_id,
            shipment_id=shipment_id,
        )

    async def add_shipment_item(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        dev_eui: str,
    ) -> BatchShipmentItem:
        return await self.shipment.add_shipment_item(
            actor=actor,
            batch_id=batch_id,
            shipment_id=shipment_id,
            dev_eui=dev_eui,
        )

    async def remove_shipment_item(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        dev_eui: str,
    ) -> None:
        return await self.shipment.remove_shipment_item(
            actor=actor,
            batch_id=batch_id,
            shipment_id=shipment_id,
            dev_eui=dev_eui,
        )

    async def complete_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
    ) -> BatchShipment:
        return await self.shipment.complete_shipment(
            actor=actor,
            batch_id=batch_id,
            shipment_id=shipment_id,
        )

    async def void_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        reason: str,
    ) -> BatchShipment:
        return await self.shipment.void_shipment(
            actor=actor,
            batch_id=batch_id,
            shipment_id=shipment_id,
            reason=reason,
        )
