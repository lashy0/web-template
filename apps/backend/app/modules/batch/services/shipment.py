from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.kg.repositories import KgRepository

from ..exceptions import (
    BatchShipmentEmptyError,
    BatchShipmentItemNotFoundError,
    BatchShipmentKgAlreadyAssignedError,
    BatchShipmentKgStateConflictError,
)
from ..models import BatchShipment, BatchShipmentItem
from ..repositories import BatchRepository, BatchShipmentRepository
from . import audit, lifecycle, queries
from .lifecycle import BATCH_EDIT_WINDOW
from .transactions import transaction


class ShipmentService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window

    async def list_shipments(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchShipment]:
        async with self._session_factory() as session:
            await queries.required_batch(
                BatchRepository(session),
                batch_id,
            )

            return await BatchShipmentRepository(session).list_by_batch(
                batch_id=batch_id,
                include_voided=include_voided,
            )

    async def get_shipped_total(self, batch_id: UUID) -> int:
        async with self._session_factory() as session:
            await queries.required_batch(
                BatchRepository(session),
                batch_id,
            )

            return await BatchShipmentRepository(session).get_shipped_total(batch_id)

    async def create_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        comment: str | None,
    ) -> BatchShipment:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_in_production(batch)

            shipment = await BatchShipmentRepository(session).create(
                batch_id=batch.id,
                comment=comment,
                created_by_user_id=actor.user_id,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch_shipment.created",
                entity=audit.shipment_entity(shipment),
                new_data={
                    "batch_id": str(batch.id),
                    "comment": shipment.comment,
                },
            )

            return shipment

    async def update_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchShipment:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_not_archived(batch)

            repository = BatchShipmentRepository(session)
            shipment = await queries.required_shipment(
                repository,
                shipment_id,
                batch_id=batch.id,
            )

            lifecycle.ensure_shipment_open(shipment)
            lifecycle.ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            if not updates:
                return shipment

            old_values = {field: getattr(shipment, field) for field in updates}

            shipment = await repository.update_details(
                shipment,
                updates=updates,
            )

            new_values = {field: getattr(shipment, field) for field in updates}

            changed = {
                field: value for field, value in new_values.items() if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=audit.audit_actor(actor),
                    action="batch_shipment.updated",
                    entity=audit.shipment_entity(shipment),
                    old_data={field: old_values[field] for field in changed},
                    new_data=changed,
                )

            return shipment

    async def list_shipment_items(
        self,
        *,
        batch_id: UUID,
        shipment_id: UUID,
    ) -> list[BatchShipmentItem]:
        async with self._session_factory() as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
            )

            repository = BatchShipmentRepository(session)

            shipment = await queries.required_shipment(
                repository,
                shipment_id,
                batch_id=batch.id,
            )

            return await repository.list_items(shipment.id)

    async def count_shipment_quantities(self, batch_id: UUID) -> dict[UUID, int]:
        async with self._session_factory() as session:
            await queries.required_batch(BatchRepository(session), batch_id)

            return await BatchShipmentRepository(session).count_items_by_batch(batch_id)

    async def count_shipment_items(
        self,
        *,
        batch_id: UUID,
        shipment_id: UUID,
    ) -> int:
        async with self._session_factory() as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
            )

            repository = BatchShipmentRepository(session)

            shipment = await queries.required_shipment(
                repository,
                shipment_id,
                batch_id=batch.id,
            )

            return await repository.count_items(shipment.id)

    async def add_shipment_item(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        dev_eui: str,
    ) -> BatchShipmentItem:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )
            lifecycle.ensure_in_production(batch)

            shipment_repository = BatchShipmentRepository(session)

            shipment = await queries.required_shipment(
                shipment_repository,
                shipment_id,
                batch_id=batch.id,
            )

            lifecycle.ensure_shipment_open(shipment)
            lifecycle.ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            kg = await KgRepository(session).get_by_dev_eui(dev_eui, for_update=True)

            if kg is None or kg.batch_id != batch.id:
                raise BatchShipmentKgStateConflictError

            existing_shipment = await shipment_repository.find_non_voided_by_kg(kg.dev_eui)

            if existing_shipment is not None:
                raise BatchShipmentKgAlreadyAssignedError

            item = await shipment_repository.add_item(
                shipment_id=shipment.id,
                kg_dev_eui=kg.dev_eui,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch_shipment.item_added",
                entity=audit.shipment_entity(shipment),
                new_data={
                    "dev_eui": kg.dev_eui,
                },
            )

            return item

    async def remove_shipment_item(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        dev_eui: str,
    ) -> None:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_not_archived(batch)

            repository = BatchShipmentRepository(session)

            shipment = await queries.required_shipment(
                repository,
                shipment_id,
                batch_id=batch.id,
            )

            lifecycle.ensure_shipment_open(shipment)
            lifecycle.ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            item = await repository.get_item(
                shipment_id=shipment.id,
                kg_dev_eui=dev_eui,
            )

            if item is None:
                raise BatchShipmentItemNotFoundError

            await repository.delete_item(item)

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch_shipment.item_removed",
                entity=audit.shipment_entity(shipment),
                old_data={
                    "dev_eui": dev_eui,
                },
            )

    async def complete_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
    ) -> BatchShipment:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_in_production(batch)

            shipment_repository = BatchShipmentRepository(session)

            shipment = await queries.required_shipment(
                shipment_repository,
                shipment_id,
                batch_id=batch.id,
            )

            lifecycle.ensure_shipment_open(shipment)
            lifecycle.ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            items = await shipment_repository.list_items(shipment.id)

            if not items:
                raise BatchShipmentEmptyError

            completed_at = datetime.now(UTC)

            shipment = await shipment_repository.complete(
                shipment,
                completed_at=completed_at,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch_shipment.completed",
                entity=audit.shipment_entity(shipment),
                old_data={
                    "completed_at": None,
                },
                new_data={
                    "completed_at": completed_at.isoformat(),
                    "quantity": len(items),
                },
            )

            return shipment

    async def void_shipment(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        reason: str,
    ) -> BatchShipment:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_not_archived(batch)

            shipment_repository = BatchShipmentRepository(session)

            shipment = await queries.required_shipment(
                shipment_repository,
                shipment_id,
                batch_id=batch.id,
            )

            lifecycle.ensure_shipment_not_voided(shipment)
            lifecycle.ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            items = await shipment_repository.list_items(shipment.id)

            voided_at = datetime.now(UTC)

            shipment = await shipment_repository.void(
                shipment,
                voided_at=voided_at,
                reason=reason,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch_shipment.voided",
                entity=audit.shipment_entity(shipment),
                old_data={
                    "voided_at": None,
                    "void_reason": None,
                },
                new_data={
                    "voided_at": voided_at.isoformat(),
                    "void_reason": reason,
                    "quantity": len(items),
                },
            )

            return shipment
