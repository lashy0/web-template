from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.batch.exceptions import (
    BatchAlreadyCompletedError,
    BatchCannotBeDeletedError,
    BatchEditNotAllowedError,
    BatchShipmentEmptyError,
    BatchShipmentKgNotPackedError,
)
from app.modules.batch.models import (
    Batch,
    BatchReceipt,
    BatchShipment,
    BatchShipmentItem,
    BatchStatus,
)
from app.modules.batch.service import BatchManagementService
from app.modules.kg.models import KgDevEuiPrefix, KgStatus, KgUnit


class _Session:
    def begin(self) -> _Session:
        return self

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _SessionFactory:
    def __call__(self) -> _Session:
        return _Session()


def _principal(*, user_id: UUID | None = None, role: Role = Role.ADMINISTRATOR) -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=user_id or uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=role,
        name="Administrator",
        login="admin",
    )


def _batch(
    *,
    batch_id: UUID | None = None,
    created_by_user_id: UUID | None = None,
    status: BatchStatus = BatchStatus.IN_PRODUCTION,
) -> Batch:
    now = datetime.now(UTC)
    return Batch(
        id=batch_id or uuid4(),
        name="August production",
        description="Initial run",
        dev_eui_prefix="a1b2c3d4e5",
        planned_qty=100,
        day_plan_qty=20,
        status=status,
        created_by_user_id=created_by_user_id,
        created_at=now,
        updated_at=now,
        completed_at=None,
        archived_at=None,
    )


def _receipt(*, batch_id: UUID, created_by_user_id: UUID | None) -> BatchReceipt:
    now = datetime.now(UTC)
    return BatchReceipt(
        id=uuid4(),
        batch_id=batch_id,
        quantity=10,
        comment="accepted",
        created_by_user_id=created_by_user_id,
        created_at=now,
        updated_at=now,
        voided_at=None,
        void_reason=None,
    )


def _shipment(*, batch_id: UUID, created_by_user_id: UUID | None) -> BatchShipment:
    now = datetime.now(UTC)
    return BatchShipment(
        id=uuid4(),
        batch_id=batch_id,
        comment="outbound",
        created_by_user_id=created_by_user_id,
        created_at=now,
        updated_at=now,
        completed_at=None,
        voided_at=None,
        void_reason=None,
    )


def _kg(*, batch_id: UUID, status: KgStatus = KgStatus.PACKED) -> KgUnit:
    now = datetime.now(UTC)
    return KgUnit(
        dev_eui="a1b2c3d4e5f60708",
        short_id="kg-000001",
        batch_id=batch_id,
        status=status,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def dependencies(
    mocker: MockerFixture,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    batches = mocker.patch("app.modules.batch.service.BatchRepository")
    batches.return_value.get_by_id = AsyncMock()
    batches.return_value.create = AsyncMock()
    batches.return_value.update_details = AsyncMock()
    batches.return_value.update_completed = AsyncMock()
    batches.return_value.delete = AsyncMock()

    receipts = mocker.patch("app.modules.batch.service.BatchReceiptRepository")
    receipts.return_value.get_by_id = AsyncMock()
    receipts.return_value.create = AsyncMock()
    receipts.return_value.update_details = AsyncMock()
    receipts.return_value.void = AsyncMock()
    receipts.return_value.exists_by_batch = AsyncMock(return_value=False)

    shipments = mocker.patch("app.modules.batch.service.BatchShipmentRepository")
    shipments.return_value.get_by_id = AsyncMock()
    shipments.return_value.create = AsyncMock()
    shipments.return_value.add_item = AsyncMock()
    shipments.return_value.list_items = AsyncMock()
    shipments.return_value.complete = AsyncMock()
    shipments.return_value.void = AsyncMock()
    shipments.return_value.find_non_voided_by_kg = AsyncMock()
    shipments.return_value.exists_by_batch = AsyncMock(return_value=False)

    kg_units = mocker.patch("app.modules.batch.service.KgRepository")
    kg_units.return_value.get_by_dev_eui = AsyncMock()
    kg_units.return_value.get_many_by_dev_euis = AsyncMock()
    kg_units.return_value.update_status_many = AsyncMock()
    kg_units.return_value.lock_dev_eui_allocation = AsyncMock()
    kg_units.return_value.get_max_dev_eui_by_prefix = AsyncMock(return_value=None)
    kg_units.return_value.create_many = AsyncMock()
    kg_units.return_value.has_non_registered_by_batch = AsyncMock(return_value=False)
    kg_units.return_value.delete_by_batch = AsyncMock()

    verification_sessions = mocker.patch(
        "app.modules.batch.service.VerificationSessionRepository"
    )
    verification_sessions.return_value.exists_by_batch_id = AsyncMock(return_value=False)

    prefixes = mocker.patch("app.modules.batch.service.KgDevEuiPrefixRepository")
    prefixes.return_value.get = AsyncMock(
        return_value=KgDevEuiPrefix(
            prefix="a1b2c3d4e5",
            short_code="kg",
            name="KG",
            created_at=datetime.now(UTC),
        )
    )

    audits = mocker.patch("app.modules.batch.service.AuditService")
    audits.from_session.return_value.record = AsyncMock()
    return batches, receipts, shipments, kg_units, prefixes, audits


def _service() -> BatchManagementService:
    return BatchManagementService(cast(async_sessionmaker[AsyncSession], _SessionFactory()))


@pytest.mark.unit
async def test_create_persists_batch_for_actor_and_records_audit_event(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, _, kg_units, prefixes, audits = dependencies
    actor = _principal()
    batch = _batch(created_by_user_id=actor.user_id)
    batch.planned_qty = 68
    batches.return_value.create.return_value = batch

    created = await _service().create(
        actor=actor,
        name=batch.name,
        description=batch.description,
        dev_eui_prefix=batch.dev_eui_prefix,
        planned_qty=batch.planned_qty,
        day_plan_qty=batch.day_plan_qty,
    )

    assert created is batch
    batches.return_value.create.assert_awaited_once_with(
        name=batch.name,
        description=batch.description,
        dev_eui_prefix=batch.dev_eui_prefix,
        planned_qty=batch.planned_qty,
        day_plan_qty=20,
        created_by_user_id=actor.user_id,
    )
    prefixes.return_value.get.assert_awaited_once_with(batch.dev_eui_prefix)
    kg_units.return_value.lock_dev_eui_allocation.assert_awaited_once_with(batch.dev_eui_prefix)
    kg_units.return_value.create_many.assert_awaited_once_with(
        dev_euis=[
            "a1b2c3d4e5000001",
            "a1b2c3d4e5000002",
            "a1b2c3d4e5000003",
            "a1b2c3d4e5000004",
            "a1b2c3d4e5000005",
            "a1b2c3d4e5000006",
            "a1b2c3d4e5000007",
            "a1b2c3d4e5000008",
            "a1b2c3d4e5000009",
            "a1b2c3d4e500000a",
            "a1b2c3d4e500000b",
            "a1b2c3d4e500000c",
            "a1b2c3d4e500000d",
            "a1b2c3d4e500000e",
            "a1b2c3d4e500000f",
            "a1b2c3d4e5000010",
            "a1b2c3d4e5000011",
            "a1b2c3d4e5000012",
            "a1b2c3d4e5000013",
            "a1b2c3d4e5000014",
            "a1b2c3d4e5000015",
            "a1b2c3d4e5000016",
            "a1b2c3d4e5000017",
            "a1b2c3d4e5000018",
            "a1b2c3d4e5000019",
            "a1b2c3d4e500001a",
            "a1b2c3d4e500001b",
            "a1b2c3d4e500001c",
            "a1b2c3d4e500001d",
            "a1b2c3d4e500001e",
            "a1b2c3d4e500001f",
            "a1b2c3d4e5000020",
            "a1b2c3d4e5000021",
            "a1b2c3d4e5000022",
            "a1b2c3d4e5000023",
            "a1b2c3d4e5000024",
            "a1b2c3d4e5000025",
            "a1b2c3d4e5000026",
            "a1b2c3d4e5000027",
            "a1b2c3d4e5000028",
            "a1b2c3d4e5000029",
            "a1b2c3d4e500002a",
            "a1b2c3d4e500002b",
            "a1b2c3d4e500002c",
            "a1b2c3d4e500002d",
            "a1b2c3d4e500002e",
            "a1b2c3d4e500002f",
            "a1b2c3d4e5000030",
            "a1b2c3d4e5000031",
            "a1b2c3d4e5000032",
            "a1b2c3d4e5000033",
            "a1b2c3d4e5000034",
            "a1b2c3d4e5000035",
            "a1b2c3d4e5000036",
            "a1b2c3d4e5000037",
            "a1b2c3d4e5000038",
            "a1b2c3d4e5000039",
            "a1b2c3d4e500003a",
            "a1b2c3d4e500003b",
            "a1b2c3d4e500003c",
            "a1b2c3d4e500003d",
            "a1b2c3d4e500003e",
            "a1b2c3d4e500003f",
            "a1b2c3d4e5000040",
            "a1b2c3d4e5000041",
            "a1b2c3d4e5000042",
            "a1b2c3d4e5000043",
            "a1b2c3d4e5000044",
        ],
        short_code="kg",
        batch_id=batch.id,
    )
    assert audits.from_session.return_value.record.await_args.kwargs["action"] == "batch.created"


@pytest.mark.unit
async def test_update_rejects_a_batch_owned_by_another_manager(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, _, _, _, _ = dependencies
    batch = _batch(created_by_user_id=uuid4())
    batches.return_value.get_by_id.return_value = batch

    with pytest.raises(BatchEditNotAllowedError):
        await _service().update(
            actor=_principal(role=Role.MANAGER),
            batch_id=batch.id,
            updates={"name": "Renamed"},
        )

    batches.return_value.update_details.assert_not_awaited()


@pytest.mark.unit
async def test_complete_updates_status_and_records_audit_event(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, _, _, _, audits = dependencies
    batch = _batch()
    batches.return_value.get_by_id.return_value = batch

    async def update_completed(item: Batch, *, completed_at: datetime) -> Batch:
        item.status = BatchStatus.COMPLETED
        item.completed_at = completed_at
        return item

    batches.return_value.update_completed.side_effect = update_completed

    completed = await _service().complete(actor=_principal(), batch_id=batch.id)

    assert completed.status is BatchStatus.COMPLETED
    assert completed.completed_at is not None
    assert audits.from_session.return_value.record.await_args.kwargs["action"] == "batch.completed"


@pytest.mark.unit
async def test_delete_rejects_batch_with_verification_history(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
    mocker: MockerFixture,
) -> None:
    batches, _, _, kg_units, _, audits = dependencies
    batch = _batch()
    batches.return_value.get_by_id.return_value = batch
    verification_sessions = mocker.patch(
        "app.modules.batch.service.VerificationSessionRepository"
    )
    verification_sessions.return_value.exists_by_batch_id = AsyncMock(return_value=True)

    with pytest.raises(BatchCannotBeDeletedError):
        await _service().delete(actor=_principal(), batch_id=batch.id)

    verification_sessions.return_value.exists_by_batch_id.assert_awaited_once_with(batch.id)
    kg_units.return_value.delete_by_batch.assert_not_awaited()
    batches.return_value.delete.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_create_receipt_rejects_completed_batch(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, receipts, _, _, _, _ = dependencies
    batch = _batch(status=BatchStatus.COMPLETED)
    batches.return_value.get_by_id.return_value = batch

    with pytest.raises(BatchAlreadyCompletedError):
        await _service().create_receipt(
            actor=_principal(),
            batch_id=batch.id,
            quantity=10,
            comment="accepted",
        )

    receipts.return_value.create.assert_not_awaited()


@pytest.mark.unit
async def test_create_receipt_records_batch_activity(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, receipts, _, _, _, audits = dependencies
    actor = _principal()
    batch = _batch()
    receipt = _receipt(batch_id=batch.id, created_by_user_id=actor.user_id)
    batches.return_value.get_by_id.return_value = batch
    receipts.return_value.create.return_value = receipt

    created = await _service().create_receipt(
        actor=actor,
        batch_id=batch.id,
        quantity=receipt.quantity,
        comment=receipt.comment,
    )

    assert created is receipt
    assert (
        audits.from_session.return_value.record.await_args.kwargs["action"]
        == "batch_receipt.created"
    )


@pytest.mark.unit
async def test_add_shipment_item_requires_packed_kg(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, shipments, kg_units, _, _ = dependencies
    actor = _principal()
    batch = _batch()
    shipment = _shipment(batch_id=batch.id, created_by_user_id=actor.user_id)
    batches.return_value.get_by_id.return_value = batch
    shipments.return_value.get_by_id.return_value = shipment
    kg_units.return_value.get_by_dev_eui.return_value = _kg(
        batch_id=batch.id,
        status=KgStatus.TESTING,
    )

    with pytest.raises(BatchShipmentKgNotPackedError):
        await _service().add_shipment_item(
            actor=actor,
            batch_id=batch.id,
            shipment_id=shipment.id,
            dev_eui="a1b2c3d4e5f60708",
        )

    shipments.return_value.add_item.assert_not_awaited()


@pytest.mark.unit
async def test_add_shipment_item_persists_packed_kg_and_records_audit_event(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, shipments, kg_units, _, audits = dependencies
    actor = _principal()
    batch = _batch()
    shipment = _shipment(batch_id=batch.id, created_by_user_id=actor.user_id)
    kg = _kg(batch_id=batch.id)
    item = BatchShipmentItem(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui)
    batches.return_value.get_by_id.return_value = batch
    shipments.return_value.get_by_id.return_value = shipment
    shipments.return_value.find_non_voided_by_kg.return_value = None
    shipments.return_value.add_item.return_value = item
    kg_units.return_value.get_by_dev_eui.return_value = kg

    created = await _service().add_shipment_item(
        actor=actor,
        batch_id=batch.id,
        shipment_id=shipment.id,
        dev_eui=kg.dev_eui,
    )

    assert created is item
    shipments.return_value.add_item.assert_awaited_once_with(
        shipment_id=shipment.id,
        kg_dev_eui=kg.dev_eui,
    )
    assert (
        audits.from_session.return_value.record.await_args.kwargs["action"]
        == "batch_shipment.item_added"
    )


@pytest.mark.unit
async def test_complete_shipment_rejects_empty_shipment(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, shipments, _, _, _ = dependencies
    actor = _principal()
    batch = _batch()
    shipment = _shipment(batch_id=batch.id, created_by_user_id=actor.user_id)
    batches.return_value.get_by_id.return_value = batch
    shipments.return_value.get_by_id.return_value = shipment
    shipments.return_value.list_items.return_value = []

    with pytest.raises(BatchShipmentEmptyError):
        await _service().complete_shipment(actor=actor, batch_id=batch.id, shipment_id=shipment.id)

    shipments.return_value.complete.assert_not_awaited()


@pytest.mark.unit
async def test_complete_shipment_marks_kg_as_shipped_and_records_audit_event(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, shipments, kg_units, _, audits = dependencies
    actor = _principal()
    batch = _batch()
    shipment = _shipment(batch_id=batch.id, created_by_user_id=actor.user_id)
    kg = _kg(batch_id=batch.id)
    item = BatchShipmentItem(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui)
    batches.return_value.get_by_id.return_value = batch
    shipments.return_value.get_by_id.return_value = shipment
    shipments.return_value.list_items.return_value = [item]
    shipments.return_value.complete.return_value = shipment
    kg_units.return_value.get_many_by_dev_euis.return_value = [kg]

    completed = await _service().complete_shipment(
        actor=actor,
        batch_id=batch.id,
        shipment_id=shipment.id,
    )

    assert completed is shipment
    kg_units.return_value.update_status_many.assert_awaited_once_with([kg], status=KgStatus.SHIPPED)
    assert (
        audits.from_session.return_value.record.await_args.kwargs["action"]
        == "batch_shipment.completed"
    )


@pytest.mark.unit
async def test_void_completed_shipment_returns_kg_to_packed(
    dependencies: tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    batches, _, shipments, kg_units, _, audits = dependencies
    actor = _principal()
    batch = _batch()
    shipment = _shipment(batch_id=batch.id, created_by_user_id=actor.user_id)
    shipment.completed_at = datetime.now(UTC) - timedelta(minutes=5)
    kg = _kg(batch_id=batch.id, status=KgStatus.SHIPPED)
    item = BatchShipmentItem(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui)
    batches.return_value.get_by_id.return_value = batch
    shipments.return_value.get_by_id.return_value = shipment
    shipments.return_value.list_items.return_value = [item]
    shipments.return_value.void.return_value = shipment
    kg_units.return_value.get_many_by_dev_euis.return_value = [kg]

    voided = await _service().void_shipment(
        actor=actor,
        batch_id=batch.id,
        shipment_id=shipment.id,
        reason="customer cancellation",
    )

    assert voided is shipment
    kg_units.return_value.update_status_many.assert_awaited_once_with([kg], status=KgStatus.PACKED)
    assert (
        audits.from_session.return_value.record.await_args.kwargs["action"]
        == "batch_shipment.voided"
    )
