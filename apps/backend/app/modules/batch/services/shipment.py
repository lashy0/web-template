"""Legacy API facade delegating shipment work to production.shipments."""

from collections.abc import Mapping
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches.repository import BatchRepository
from app.contexts.production.kg.repository import KgRepository
from app.contexts.production.preparation.repository import PreparationRepository
from app.contexts.production.shipments.commands import (
    AddShipmentItem,
    CompleteShipment,
    CreateShipment,
    RemoveShipmentItem,
    UpdateShipment,
    VoidShipment,
)
from app.contexts.production.shipments.model import BatchShipment, BatchShipmentItem
from app.contexts.production.shipments.queries import ShipmentQueries
from app.contexts.production.shipments.repository import ShipmentRepository
from app.shared.security import CurrentPrincipal
from app.shared.uow import transaction

from .lifecycle import BATCH_EDIT_WINDOW


class ShipmentService:
    """Compatibility session runner; shipment policy is exclusively in new commands."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window

    async def list_shipments(
        self, batch_id: UUID, *, include_voided: bool = False
    ) -> list[BatchShipment]:
        async with self._session_factory() as session:
            return await ShipmentQueries(
                BatchRepository(session), ShipmentRepository(session)
            ).list_by_batch(batch_id, include_voided=include_voided)

    async def get_shipped_total(self, batch_id: UUID) -> int:
        async with self._session_factory() as session:
            return await ShipmentQueries(
                BatchRepository(session), ShipmentRepository(session)
            ).shipped_total(batch_id)

    async def list_shipment_items(
        self, *, batch_id: UUID, shipment_id: UUID
    ) -> list[BatchShipmentItem]:
        async with self._session_factory() as session:
            return await ShipmentQueries(
                BatchRepository(session), ShipmentRepository(session)
            ).list_items(batch_id=batch_id, shipment_id=shipment_id)

    async def count_shipment_quantities(self, batch_id: UUID) -> dict[UUID, int]:
        async with self._session_factory() as session:
            return await ShipmentQueries(
                BatchRepository(session), ShipmentRepository(session)
            ).item_counts(batch_id)

    async def count_shipment_items(self, *, batch_id: UUID, shipment_id: UUID) -> int:
        async with self._session_factory() as session:
            return await ShipmentQueries(
                BatchRepository(session), ShipmentRepository(session)
            ).item_count(batch_id=batch_id, shipment_id=shipment_id)

    async def create_shipment(
        self, *, actor: CurrentPrincipal, batch_id: UUID, comment: str | None
    ) -> BatchShipment:
        async with transaction(self._session_factory) as session:
            return await CreateShipment(
                BatchRepository(session),
                ShipmentRepository(session),
                PreparationRepository(session),
                TransactionalAuditWriter.from_session(session),
            ).execute(actor=actor, batch_id=batch_id, comment=comment)

    async def update_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchShipment:
        async with transaction(self._session_factory) as session:
            return await UpdateShipment(
                BatchRepository(session),
                ShipmentRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, shipment_id=shipment_id, updates=updates)

    async def add_shipment_item(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        dev_eui: str,
    ) -> BatchShipmentItem:
        async with transaction(self._session_factory) as session:
            return await AddShipmentItem(
                BatchRepository(session),
                ShipmentRepository(session),
                KgRepository(session),
                PreparationRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, shipment_id=shipment_id, dev_eui=dev_eui)

    async def remove_shipment_item(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        dev_eui: str,
    ) -> None:
        async with transaction(self._session_factory) as session:
            await RemoveShipmentItem(
                BatchRepository(session),
                ShipmentRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, shipment_id=shipment_id, dev_eui=dev_eui)

    async def complete_shipment(
        self, *, actor: CurrentPrincipal, batch_id: UUID, shipment_id: UUID
    ) -> BatchShipment:
        async with transaction(self._session_factory) as session:
            return await CompleteShipment(
                BatchRepository(session),
                ShipmentRepository(session),
                PreparationRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, shipment_id=shipment_id)

    async def void_shipment(
        self, *, actor: CurrentPrincipal, batch_id: UUID, shipment_id: UUID, reason: str
    ) -> BatchShipment:
        async with transaction(self._session_factory) as session:
            return await VoidShipment(
                BatchRepository(session),
                ShipmentRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, shipment_id=shipment_id, reason=reason)
