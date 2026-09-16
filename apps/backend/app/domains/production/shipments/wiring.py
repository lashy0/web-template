from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.domains.production.batches.repository import BatchRepository
from app.domains.production.batches.rules import BATCH_EDIT_WINDOW
from app.domains.production.kg.repository import KgRepository
from app.domains.production.preparation.repository import PreparationRepository

from .commands import (
    AddShipmentItem,
    CompleteShipment,
    CreateShipment,
    RemoveShipmentItem,
    UpdateShipment,
    VoidShipment,
)
from .queries import ShipmentQueries
from .repository import ShipmentRepository


def create_queries(session: AsyncSession) -> ShipmentQueries:
    return ShipmentQueries(BatchRepository(session), ShipmentRepository(session))


async def shipment_item_count(session: AsyncSession, shipment_id: UUID) -> int:
    return await ShipmentRepository(session).item_count(shipment_id)


def create_shipment_command(session: AsyncSession) -> CreateShipment:
    return CreateShipment(
        BatchRepository(session),
        ShipmentRepository(session),
        PreparationRepository(session),
        TransactionalAuditWriter.from_session(session),
    )


def update_shipment_command(session: AsyncSession) -> UpdateShipment:
    return UpdateShipment(
        BatchRepository(session),
        ShipmentRepository(session),
        TransactionalAuditWriter.from_session(session),
        edit_window=BATCH_EDIT_WINDOW,
    )


def add_shipment_item_command(session: AsyncSession) -> AddShipmentItem:
    return AddShipmentItem(
        BatchRepository(session),
        ShipmentRepository(session),
        KgRepository(session),
        PreparationRepository(session),
        TransactionalAuditWriter.from_session(session),
        edit_window=BATCH_EDIT_WINDOW,
    )


def remove_shipment_item_command(session: AsyncSession) -> RemoveShipmentItem:
    return RemoveShipmentItem(
        BatchRepository(session),
        ShipmentRepository(session),
        TransactionalAuditWriter.from_session(session),
        edit_window=BATCH_EDIT_WINDOW,
    )


def complete_shipment_command(session: AsyncSession) -> CompleteShipment:
    return CompleteShipment(
        BatchRepository(session),
        ShipmentRepository(session),
        PreparationRepository(session),
        TransactionalAuditWriter.from_session(session),
        edit_window=BATCH_EDIT_WINDOW,
    )


def void_shipment_command(session: AsyncSession) -> VoidShipment:
    return VoidShipment(
        BatchRepository(session),
        ShipmentRepository(session),
        TransactionalAuditWriter.from_session(session),
        edit_window=BATCH_EDIT_WINDOW,
    )
