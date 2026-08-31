from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.batch.exceptions import (
    BatchAlreadyCompletedError,
    BatchArchivedError,
    BatchCannotBeDeletedError,
    BatchDevEuiPrefixNotFoundError,
    BatchDevEuiRangeOverflowError,
    BatchEditNotAllowedError,
    BatchEditWindowExpiredError,
    BatchNotFoundError,
    BatchReceiptAlreadyVoidedError,
    BatchReceiptEditNotAllowedError,
    BatchReceiptEditWindowExpiredError,
    BatchReceiptNotFoundError,
    BatchShipmentAlreadyCompletedError,
    BatchShipmentAlreadyVoidedError,
    BatchShipmentEditNotAllowedError,
    BatchShipmentEditWindowExpiredError,
    BatchShipmentEmptyError,
    BatchShipmentItemNotFoundError,
    BatchShipmentKgAlreadyAssignedError,
    BatchShipmentKgNotFoundError,
    BatchShipmentKgNotPackedError,
    BatchShipmentKgWrongBatchError,
    BatchShipmentNotFoundError,
)
from app.modules.batch.models import (
    Batch,
    BatchReceipt,
    BatchShipment,
    BatchShipmentItem,
    BatchStatus,
)
from app.modules.batch.repository import (
    BatchReceiptRepository,
    BatchRepository,
    BatchShipmentRepository,
)
from app.modules.kg.models import KgStatus
from app.modules.kg.repository import KgRepository, KgDevEuiPrefixRepository


BATCH_EDIT_WINDOW = timedelta(minutes=60)


class BatchManagementService:
    """Coordinates batch lifecycle, receipts, shipments, KG state, and audit."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window

    # Batch

    async def get(self, batch_id: UUID) -> Batch | None:
        async with self._session_factory() as session:
            return await BatchRepository(session).get_by_id(batch_id)

    async def list(self, **filters: object) -> tuple[list[Batch], int]:
        async with self._session_factory() as session:
            return await BatchRepository(session).search(**filters) # type: ignore[arg-type]

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
    ) -> Batch:
        async with self._session_factory() as session, session.begin():
            batch_repository = BatchRepository(session)
            kg_repository = KgRepository(session)
            prefix_repository = KgDevEuiPrefixRepository(session)

            prefix = await prefix_repository.get(dev_eui_prefix)

            if prefix is None:
                raise BatchDevEuiPrefixNotFoundError

            await kg_repository.lock_dev_eui_allocation(prefix.prefix)

            max_dev_eui = (
                await kg_repository.get_max_dev_eui_by_prefix(
                    prefix.prefix
                )
            )

            if max_dev_eui is None:
                start_suffix = 1
            else:
                start_suffix = int(max_dev_eui[-6:], 16) + 1

            end_suffix = start_suffix + planned_qty - 1

            if end_suffix > 0xFFFFFF:
                raise BatchDevEuiRangeOverflowError

            dev_euis = [
                (
                    f"{prefix.prefix}"
                    f"{start_suffix + offset:06x}"
                )
                for offset in range(planned_qty)
            ]

            batch = await batch_repository.create(
                name=name,
                description=description,
                dev_eui_prefix=prefix.prefix,
                planned_qty=planned_qty,
                day_plan_qty=day_plan_qty,
                created_by_user_id=actor.user_id,
            )

            kg_units = await kg_repository.create_many(
                dev_euis=dev_euis,
                short_code=prefix.short_code,
                batch_id=batch.id,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch.created",
                entity=self._batch_entity(batch),
                new_data={
                    "name": batch.name,
                    "description": batch.description,
                    "dev_eui_prefix": prefix.prefix,
                    "dev_eui_start": dev_euis[0],
                    "dev_eui_end": dev_euis[-1],
                    "planned_qty": batch.planned_qty,
                    "day_plan_qty": batch.day_plan_qty,
                    "status": batch.status.value,
                    "kg_quantity": len(kg_units),
                },
            )

            return batch

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        updates: Mapping[str, object],
    ) -> Batch:
        async with self._session_factory() as session, session.begin():
            repository = BatchRepository(session)
            batch = await self._required_batch(repository, batch_id)

            self._ensure_not_archived(batch)
            self._ensure_batch_edit_allowed(
                batch,
                actor=actor,
                now=datetime.now(UTC),
            )

            if not updates:
                return batch

            old_values = {
                field: getattr(batch, field)
                for field in updates
            }

            batch = await repository.update_details(
                batch,
                updates=updates,
            )

            new_values = {
                field: getattr(batch, field)
                for field in updates
            }

            changed = {
                field: value
                for field, value in new_values.items()
                if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=self._audit_actor(actor),
                    action="batch.updated",
                    entity=self._batch_entity(batch),
                    old_data={
                        field: old_values[field]
                        for field in changed
                    },
                    new_data=changed,
                )

            return batch

    async def complete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> Batch:
        async with self._session_factory() as session, session.begin():
            repository = BatchRepository(session)
            batch = await self._required_batch(repository, batch_id)

            self._ensure_not_archived(batch)

            if batch.status == BatchStatus.COMPLETED:
                raise BatchAlreadyCompletedError

            old_status = batch.status
            completed_at = datetime.now(UTC)

            batch = await repository.update_completed(
                batch,
                completed_at=completed_at,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch.completed",
                entity=self._batch_entity(batch),
                old_data={
                    "status": old_status.value,
                    "completed_at": None,
                },
                new_data={
                    "status": batch.status.value,
                    "completed_at": completed_at.isoformat(),
                },
            )

            return batch

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        archived: bool,
    ) -> Batch:
        async with self._session_factory() as session, session.begin():
            repository = BatchRepository(session)
            batch = await self._required_batch(repository, batch_id)

            if archived:
                if batch.archived_at is not None:
                    return batch

                archived_at = datetime.now(UTC)

                batch = await repository.update_archived(
                    batch,
                    archived_at=archived_at,
                )

                action = "batch.archived"
                old_data = {
                    "archived_at": None,
                }

                new_data = {
                    "archived_at": archived_at.isoformat(),
                }

            else:
                if batch.archived_at is None:
                    return batch

                old_archived_at = batch.archived_at

                batch = await repository.update_archived(
                    batch,
                    archived_at=None,
                )

                action = "batch.restored"
                old_data = {
                    "archived_at": old_archived_at.isoformat(),
                }

                new_data = {
                    "archived_at": None,
                }

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action=action,
                entity=self._batch_entity(batch),
                old_data=old_data,
                new_data=new_data,
            )

            return batch

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            batch_repository = BatchRepository(session)
            receipt_repository = BatchReceiptRepository(session)
            shipment_repository = BatchShipmentRepository(session)
            kg_repository = KgRepository(session)

            batch = await self._required_batch(
                batch_repository,
                batch_id,
            )

            self._ensure_batch_edit_allowed(
                batch,
                actor=actor,
                now=datetime.now(UTC),
            )

            if batch.status != BatchStatus.IN_PRODUCTION:
                raise BatchCannotBeDeletedError

            if await receipt_repository.exists_by_batch(batch.id):
                raise BatchCannotBeDeletedError

            if await shipment_repository.exists_by_batch(batch.id):
                raise BatchCannotBeDeletedError

            if await kg_repository.has_non_registered_by_batch(batch.id):
                raise BatchCannotBeDeletedError

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch.deleted",
                entity=self._batch_entity(batch),
                old_data={
                    "name": batch.name,
                    "description": batch.description,
                    "planned_qty": batch.planned_qty,
                    "day_plan_qty": batch.day_plan_qty,
                    "status": batch.status.value,
                },
            )

            await kg_repository.delete_by_batch(batch.id)
            await batch_repository.delete(batch)

    # Receipts

    async def list_receipts(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchReceipt]:
        async with self._session_factory() as session:
            await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            return await BatchReceiptRepository(session).list_by_batch(
                batch_id,
                include_voided=include_voided,
            )

    async def get_received_total(self, batch_id: UUID) -> int:
        async with self._session_factory() as session:
            await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            return await BatchReceiptRepository(session).get_total(batch_id)

    async def create_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        quantity: int,
        comment: str | None,
    ) -> BatchReceipt:
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            self._ensure_in_production(batch)

            receipt = await BatchReceiptRepository(session).create(
                batch_id=batch.id,
                quantity=quantity,
                comment=comment,
                created_by_user_id=actor.user_id,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch_receipt.created",
                entity=self._receipt_entity(receipt),
                new_data={
                    "batch_id": str(batch.id),
                    "quantity": receipt.quantity,
                    "comment": receipt.comment,
                },
            )

            return receipt

    async def update_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchReceipt:
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )
            self._ensure_not_archived(batch)

            repository = BatchReceiptRepository(session)
            receipt = await self._required_receipt(
                repository,
                receipt_id,
                batch_id=batch.id,
            )

            self._ensure_receipt_active(receipt)
            self._ensure_receipt_edit_allowed(
                receipt,
                actor=actor,
                now=datetime.now(UTC),
            )

            if not updates:
                return receipt

            old_values = {
                field: getattr(receipt, field)
                for field in updates
            }

            receipt = await repository.update_details(
                receipt,
                updates=updates,
            )

            new_values = {
                field: getattr(receipt, field)
                for field in updates
            }

            changed = {
                field: value
                for field, value in new_values.items()
                if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=self._audit_actor(actor),
                    action="batch_receipt.updated",
                    entity=self._receipt_entity(receipt),
                    old_data={
                        field: old_values[field]
                        for field in changed
                    },
                    new_data=changed,
                )

            return receipt

    async def void_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        reason: str,
    ) -> BatchReceipt:
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )
            self._ensure_not_archived(batch)

            repository = BatchReceiptRepository(session)
            receipt = await self._required_receipt(
                repository,
                receipt_id,
                batch_id=batch.id,
            )

            self._ensure_receipt_active(receipt)
            self._ensure_receipt_edit_allowed(
                receipt,
                actor=actor,
                now=datetime.now(UTC),
            )

            voided_at = datetime.now(UTC)

            receipt = await repository.void(
                receipt,
                voided_at=voided_at,
                reason=reason,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch_receipt.voided",
                entity=self._receipt_entity(receipt),
                old_data={
                    "voided_at": None,
                    "void_reason": None,
                },
                new_data={
                    "voided_at": voided_at.isoformat(),
                    "void_reason": reason,
                },
            )

            return receipt

    # Shipment

    async def list_shipments(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchShipment]:
        async with self._session_factory() as session:
            await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            return await BatchShipmentRepository(session).list_by_batch(
                batch_id=batch_id,
                include_voided=include_voided,
            )

    async def get_shipped_total(self, batch_id: UUID) -> int:
        async with self._session_factory() as session:
            await self._required_batch(
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
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            self._ensure_in_production(batch)

            shipment = await BatchShipmentRepository(session).create(
                batch_id=batch.id,
                comment=comment,
                created_by_user_id=actor.user_id,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch_shipment.created",
                entity=self._shipment_entity(shipment),
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
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            self._ensure_not_archived(batch)

            repository = BatchShipmentRepository(session)
            shipment = await self._required_shipment(
                repository,
                shipment_id,
                batch_id=batch.id,
            )

            self._ensure_shipment_open(shipment)
            self._ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
            )

            if not updates:
                return shipment

            old_values = {
                field: getattr(shipment, field)
                for field in updates
            }

            shipment = await repository.update_details(
                shipment,
                updates=updates,
            )

            new_values = {
                field: getattr(shipment, field)
                for field in updates
            }

            changed  = {
                field: value
                for field, value in new_values.items()
                if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=self._audit_actor(actor),
                    action="batch_shipment.updated",
                    entity=self._shipment_entity(shipment),
                    old_data={
                        field: old_values[field]
                        for field in changed
                    },
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
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            repository = BatchShipmentRepository(session)

            shipment = await self._required_shipment(
                repository,
                shipment_id,
                batch_id=batch.id,
            )

            return await repository.list_items(shipment.id)

    async def count_shipment_items(
        self,
        *,
        batch_id: UUID,
        shipment_id: UUID,
    ) -> int:
        async with self._session_factory() as session:
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            repository = BatchShipmentRepository(session)

            shipment = await self._required_shipment(
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
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )
            self._ensure_in_production(batch)

            shipment_repository = BatchShipmentRepository(session)

            shipment = await self._required_shipment(
                shipment_repository,
                shipment_id,
                batch_id=batch.id,
            )

            self._ensure_shipment_open(shipment)
            self._ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
            )

            kg_repository = KgRepository(session)
            kg = await kg_repository.get_by_dev_eui(dev_eui)

            if kg is None:
                raise BatchShipmentKgNotFoundError

            if kg.batch_id != batch.id:
                raise BatchShipmentKgWrongBatchError

            if kg.status != KgStatus.PACKED:
                raise BatchShipmentKgNotPackedError

            existing_shipment  = (
                await shipment_repository.find_non_voided_by_kg(
                    kg.dev_eui
                )
            )

            if existing_shipment is not None:
                raise BatchShipmentKgAlreadyAssignedError

            item = await shipment_repository.add_item(
                shipment_id=shipment.id,
                kg_dev_eui=kg.dev_eui,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch_shipment.item_added",
                entity=self._shipment_entity(shipment),
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
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            self._ensure_not_archived(batch)

            repository = BatchShipmentRepository(session)

            shipment = await self._required_shipment(
                repository,
                shipment_id,
                batch_id=batch.id,
            )

            self._ensure_shipment_open(shipment)
            self._ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
            )

            item = await repository.get_item(
                shipment_id=shipment.id,
                kg_dev_eui=dev_eui,
            )

            if item is None:
                raise BatchShipmentItemNotFoundError

            await repository.delete_item(item)

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch_shipment.item_removed",
                entity=self._shipment_entity(shipment),
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
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            self._ensure_in_production(batch)

            shipment_repository  = BatchShipmentRepository(session)

            shipment = await self._required_shipment(
                shipment_repository,
                shipment_id,
                batch_id=batch.id,
            )

            self._ensure_shipment_open(shipment)
            self._ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
            )

            items = await shipment_repository.list_items(shipment.id)

            if not items:
                raise BatchShipmentEmptyError

            dev_euis = [
                item.kg_dev_eui
                for item in items
            ]

            kg_repository = KgRepository(session)

            kg_units = await kg_repository.get_many_by_dev_euis(dev_euis)

            if len(kg_units) != len(dev_euis):
                raise BatchShipmentKgNotFoundError

            if any(
                kg.batch_id != batch.id
                for kg in kg_units
            ):
                raise BatchShipmentKgWrongBatchError

            if any(
                kg.status != KgStatus.PACKED
                for kg in kg_units
            ):
                raise BatchShipmentKgNotPackedError

            await kg_repository.update_status_many(
                kg_units,
                status=KgStatus.SHIPPED,
            )

            completed_at = datetime.now(UTC)

            shipment = await shipment_repository.complete(
                shipment,
                completed_at=completed_at,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch_shipment.completed",
                entity=self._shipment_entity(shipment),
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
        async with self._session_factory() as session, session.begin():
            batch = await self._required_batch(
                BatchRepository(session),
                batch_id,
            )

            self._ensure_not_archived(batch)

            shipment_repository = BatchShipmentRepository(session)

            shipment = await self._required_shipment(
                shipment_repository,
                shipment_id,
                batch_id=batch.id,
            )

            self._ensure_shipment_not_voided(shipment)
            self._ensure_shipment_edit_allowed(
                shipment,
                actor=actor,
                now=datetime.now(UTC),
            )

            items = await shipment_repository.list_items(shipment.id)

            if shipment.completed_at is not None and items:
                dev_euis = [
                    item.kg_dev_eui
                    for item in items
                ]

                kg_repository = KgRepository(session)

                kg_units = (
                    await kg_repository.get_many_by_dev_euis(
                        dev_euis
                    )
                )

                if len(kg_units) != len(dev_euis):
                    raise BatchShipmentKgNotFoundError

                if any(
                    kg.batch_id != batch.id
                    for kg in kg_units
                ):
                    raise BatchShipmentKgWrongBatchError

                await kg_repository.update_status_many(
                    kg_units,
                    status=KgStatus.PACKED,
                )

            voided_at = datetime.now(UTC)

            shipment = await shipment_repository.void(
                shipment,
                voided_at=voided_at,
                reason=reason,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="batch_shipment.voided",
                entity=self._shipment_entity(shipment),
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

    # Helpers

    @staticmethod
    async def _required_batch(
        repository: BatchRepository,
        batch_id: UUID,
    ) -> Batch:
        batch = await repository.get_by_id(batch_id)

        if batch is None:
            raise BatchNotFoundError

        return batch

    @staticmethod
    async def _required_receipt(
        repository: BatchReceiptRepository,
        receipt_id: UUID,
        *,
        batch_id: UUID,
    ) -> BatchReceipt:
        receipt = await repository.get_by_id(receipt_id)

        if (
            receipt is None
            or receipt.batch_id != batch_id
        ):
            raise BatchReceiptNotFoundError

        return receipt

    @staticmethod
    async def _required_shipment(
        repository: BatchShipmentRepository,
        shipment_id: UUID,
        *,
        batch_id: UUID,
    ) -> BatchShipment:
        shipment = await repository.get_by_id(shipment_id)

        if (
            shipment is None
            or shipment.batch_id != batch_id
        ):
            raise BatchShipmentNotFoundError

        return shipment

    @staticmethod
    def _ensure_not_archived(batch: Batch) -> None:
        if batch.archived_at is not None:
            raise BatchArchivedError

    @classmethod
    def _ensure_in_production(cls, batch: Batch) -> None:
        cls._ensure_not_archived(batch)

        if batch.status == BatchStatus.COMPLETED:
            raise BatchAlreadyCompletedError

    def _ensure_batch_edit_allowed(
        self,
        batch: Batch,
        *,
        actor: CurrentPrincipal,
        now: datetime,
    ) -> None:
        if actor.role == Role.ADMINISTRATOR:
            return

        if batch.created_by_user_id != actor.user_id:
            raise BatchEditNotAllowedError

        if now - batch.created_at > self._edit_window:
            raise BatchEditWindowExpiredError

    @staticmethod
    def _ensure_receipt_active(receipt: BatchReceipt) -> None:
        if receipt.voided_at is not None:
            raise BatchReceiptAlreadyVoidedError

    def _ensure_receipt_edit_allowed(
        self,
        receipt: BatchReceipt,
        *,
        actor: CurrentPrincipal,
        now: datetime,
    ) -> None:
        if actor.role == Role.ADMINISTRATOR:
            return

        if receipt.created_by_user_id != actor.user_id:
            raise BatchReceiptEditNotAllowedError

        if now - receipt.created_at > self._edit_window:
            raise BatchReceiptEditWindowExpiredError

    @staticmethod
    def _ensure_shipment_not_voided(shipment: BatchShipment) -> None:
        if shipment.voided_at is not None:
            raise BatchShipmentAlreadyVoidedError

    @classmethod
    def _ensure_shipment_open(
        cls,
        shipment: BatchShipment,
    ) -> None:
        cls._ensure_shipment_not_voided(shipment)

        if shipment.completed_at is not None:
            raise BatchShipmentAlreadyCompletedError

    def _ensure_shipment_edit_allowed(
        self,
        shipment: BatchShipment,
        *,
        actor: CurrentPrincipal,
        now: datetime,
    ) -> None:
        if actor.role == Role.ADMINISTRATOR:
            return

        if shipment.created_by_user_id != actor.user_id:
            raise BatchShipmentEditNotAllowedError

        if shipment.completed_at is None:
            return

        if (
            now - shipment.completed_at
            > self._edit_window
        ):
            raise BatchShipmentEditWindowExpiredError

    @staticmethod
    def _audit_actor(actor: CurrentPrincipal) -> AuditActor:
        return AuditActor.user(
            actor.user_id,
            name=actor.name,
            login=actor.login,
        )

    @staticmethod
    def _batch_entity(batch: Batch) -> AuditEntity:
        return AuditEntity(
            type="batch",
            id=str(batch.id),
            display_name=batch.name,
            identifier=str(batch.id),
        )

    @staticmethod
    def _receipt_entity(receipt: BatchReceipt) -> AuditEntity:
        return AuditEntity(
            type="batch_receipt",
            id=str(receipt.id),
            display_name=f"Receipt {receipt.id}",
            identifier=str(receipt.batch_id),
        )

    @staticmethod
    def _shipment_entity(shipment: BatchShipment) -> AuditEntity:
        return AuditEntity(
            type="batch_shipment",
            id=str(shipment.id),
            display_name=f"Shipment {shipment.id}",
            identifier=str(shipment.batch_id),
        )
