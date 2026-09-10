import asyncio
import re
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import AuditService
from app.modules.batch.exceptions import (
    BatchShipmentAlreadyCompletedError,
    BatchShipmentKgAlreadyAssignedError,
)
from app.modules.batch.models import (
    ActivationType,
    BatchShipment,
    BatchShipmentItem,
    BatchStatus,
    LoRaWanVersion,
)
from app.modules.batch.services import BatchManagementService
from app.modules.kg.models import KgDevEuiPrefix, KgStatus, KgUnit
from app.modules.kg.services import KgManagementService
from app.modules.users.models import User

pytestmark = pytest.mark.integration


@pytest.fixture
async def scenario(database_session_factory: async_sessionmaker[AsyncSession]):
    factory = database_session_factory
    actor = CurrentPrincipal(
        user_id=uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=Role.ADMINISTRATOR,
        name="Batch integration",
        login="batch-test",
    )
    prefix = uuid4().hex[:10]
    async with factory() as session, session.begin():
        session.add(
            User(id=actor.user_id, identity_id=actor.identity_id, name=actor.name, role=actor.role)
        )
        session.add(KgDevEuiPrefix(prefix=prefix, short_code=prefix))
    service = BatchManagementService(factory)
    batch = await service.create(
        actor=actor,
        name=f"test-{uuid4()}",
        description=None,
        dev_eui_prefix=prefix,
        planned_qty=1,
        day_plan_qty=1,
        activation_type=ActivationType.OTAA,
        lorawan_version=LoRaWanVersion.V1_1,
    )
    return factory, actor, service, batch, prefix + "000001"


async def test_create_persists_generated_lorawan_config(scenario):
    _, _, service, batch, _ = scenario

    assert batch.lorawan_config is not None
    assert batch.lorawan_config.activation_type is ActivationType.OTAA
    assert batch.lorawan_config.lorawan_version is LoRaWanVersion.V1_1
    assert re.fullmatch(r"[0-9a-f]{16}", batch.lorawan_config.join_eui)

    loaded = await service.get(batch.id)
    assert loaded is not None
    assert loaded.lorawan_config is not None
    assert loaded.lorawan_config.join_eui == batch.lorawan_config.join_eui


async def test_full_lifecycle_restores_kg_and_records_audit(scenario):
    factory, actor, service, batch, dev_eui = scenario
    await service.create_receipt(actor=actor, batch_id=batch.id, quantity=1, comment=None)
    kg_service = KgManagementService(factory)
    await kg_service.set_status(actor=actor, dev_eui=dev_eui, status=KgStatus.PACKED)
    shipment = await service.create_shipment(actor=actor, batch_id=batch.id, comment=None)
    await service.add_shipment_item(
        actor=actor, batch_id=batch.id, shipment_id=shipment.id, dev_eui=dev_eui
    )
    await service.complete_shipment(actor=actor, batch_id=batch.id, shipment_id=shipment.id)
    assert (await kg_service.get(dev_eui)).status == KgStatus.SHIPPED
    assert await service.get_shipped_total(batch.id) == 1
    await service.void_shipment(
        actor=actor, batch_id=batch.id, shipment_id=shipment.id, reason="Returned"
    )
    assert (await kg_service.get(dev_eui)).status == KgStatus.PACKED
    assert await service.get_shipped_total(batch.id) == 0
    assert (await service.complete(actor=actor, batch_id=batch.id)).status == BatchStatus.COMPLETED
    assert (await service.set_archived(actor=actor, batch_id=batch.id, archived=True)).archived_at
    async with factory() as session:
        actions = list(
            await session.scalars(
                select(AuditEvent.action).where(AuditEvent.actor_id == str(actor.user_id))
            )
        )
    for action in [
        "batch.created",
        "batch_receipt.created",
        "batch_shipment.created",
        "batch_shipment.item_added",
        "batch_shipment.completed",
        "batch_shipment.voided",
        "batch.completed",
        "batch.archived",
    ]:
        assert actions.count(action) == 1


@pytest.mark.parametrize("same_shipment", [False, True])
async def test_concurrent_add_has_one_winner_and_one_domain_conflict(
    scenario, monkeypatch, same_shipment
):
    factory, actor, service, batch, dev_eui = scenario
    await KgManagementService(factory).set_status(
        actor=actor, dev_eui=dev_eui, status=KgStatus.PACKED
    )
    shipments = [
        await service.create_shipment(actor=actor, batch_id=batch.id, comment=None)
        for _ in range(2)
    ]
    if same_shipment:
        shipments[1] = shipments[0]
    # Hold the winner immediately before insertion, while the second transaction
    # has begun its SELECT FOR UPDATE. Without that lock both checks see no item.
    from app.modules.batch.repositories import BatchRepository, BatchShipmentRepository

    original_get = BatchRepository.get_by_id
    original_add = BatchShipmentRepository.add_item
    first_at_insert = asyncio.Event()
    second_at_lock = asyncio.Event()
    calls = 0
    second_pid = None

    async def get(repository, batch_id, *, for_update=False):
        nonlocal calls, second_pid
        calls += 1
        if calls == 2:
            second_pid = await repository._session.scalar(select(func.pg_backend_pid()))
            second_at_lock.set()
        return await original_get(repository, batch_id, for_update=for_update)

    async def add(repository, **kwargs):
        first_at_insert.set()
        await asyncio.wait_for(second_at_lock.wait(), 5)

        async def wait_for_database_lock():
            while not await repository._session.scalar(select(func.pg_blocking_pids(second_pid))):
                await asyncio.sleep(0.01)

        # Assert real DB blocking, not merely overlapping task scheduling.
        await asyncio.wait_for(wait_for_database_lock(), 5)
        return await original_add(repository, **kwargs)

    monkeypatch.setattr(BatchRepository, "get_by_id", get)
    monkeypatch.setattr(BatchShipmentRepository, "add_item", add)

    async def assign(shipment):
        return await service.add_shipment_item(
            actor=actor, batch_id=batch.id, shipment_id=shipment.id, dev_eui=dev_eui
        )

    first = asyncio.create_task(assign(shipments[0]))
    await asyncio.wait_for(first_at_insert.wait(), 5)
    results = await asyncio.gather(first, assign(shipments[1]), return_exceptions=True)
    assert sum(isinstance(result, BatchShipmentItem) for result in results) == 1
    assert sum(isinstance(result, BatchShipmentKgAlreadyAssignedError) for result in results) == 1
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(BatchShipmentItem)
                .where(BatchShipmentItem.kg_dev_eui == dev_eui)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.actor_id == str(actor.user_id),
                    AuditEvent.action == "batch_shipment.item_added",
                )
            )
            == 1
        )


@pytest.mark.parametrize("operation", ["add", "complete", "void"])
async def test_audit_failure_rolls_back_entire_shipment_operation(scenario, monkeypatch, operation):
    factory, actor, service, batch, dev_eui = scenario
    await KgManagementService(factory).set_status(
        actor=actor, dev_eui=dev_eui, status=KgStatus.PACKED
    )
    shipment = await service.create_shipment(actor=actor, batch_id=batch.id, comment=None)
    kwargs = {"actor": actor, "batch_id": batch.id, "shipment_id": shipment.id}
    if operation != "add":
        await service.add_shipment_item(**kwargs, dev_eui=dev_eui)
    if operation == "void":
        await service.complete_shipment(**kwargs)

    original_record = AuditService.record

    async def fail_after_record(self, **kwargs):
        await original_record(self, **kwargs)
        raise RuntimeError("audit storage failure")

    monkeypatch.setattr(AuditService, "record", fail_after_record)
    with pytest.raises(RuntimeError, match="audit storage failure"):
        if operation == "add":
            await service.add_shipment_item(**kwargs, dev_eui=dev_eui)
        elif operation == "complete":
            await service.complete_shipment(**kwargs)
        else:
            await service.void_shipment(**kwargs, reason="return")
    async with factory() as session:
        stored = await session.get(BatchShipment, shipment.id)
        kg = await session.get(KgUnit, dev_eui)
        assert stored.voided_at is None
        assert (stored.completed_at is not None) == (operation == "void")
        assert kg.status == (KgStatus.SHIPPED if operation == "void" else KgStatus.PACKED)
        assert await session.scalar(
            select(func.count())
            .select_from(BatchShipmentItem)
            .where(BatchShipmentItem.shipment_id == shipment.id)
        ) == (0 if operation == "add" else 1)
        action = {"add": "item_added", "complete": "completed", "void": "voided"}[operation]
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.entity_id == str(shipment.id),
                    AuditEvent.action == f"batch_shipment.{action}",
                )
            )
            == 0
        )


async def test_parallel_completion_then_void_releases_kg_for_another_shipment(scenario):
    factory, actor, service, batch, dev_eui = scenario
    await KgManagementService(factory).set_status(
        actor=actor, dev_eui=dev_eui, status=KgStatus.PACKED
    )
    shipment = await service.create_shipment(actor=actor, batch_id=batch.id, comment=None)
    kwargs = {"actor": actor, "batch_id": batch.id, "shipment_id": shipment.id}
    await service.add_shipment_item(**kwargs, dev_eui=dev_eui)
    results = await asyncio.gather(
        service.complete_shipment(**kwargs),
        service.complete_shipment(**kwargs),
        return_exceptions=True,
    )
    assert sum(isinstance(result, BatchShipment) for result in results) == 1
    assert sum(isinstance(result, BatchShipmentAlreadyCompletedError) for result in results) == 1
    await service.void_shipment(**kwargs, reason="return")
    replacement = await service.create_shipment(actor=actor, batch_id=batch.id, comment=None)
    await service.add_shipment_item(
        actor=actor, batch_id=batch.id, shipment_id=replacement.id, dev_eui=dev_eui
    )
    assert await service.count_shipment_items(batch_id=batch.id, shipment_id=shipment.id) == 1
    assert await service.count_shipment_items(batch_id=batch.id, shipment_id=replacement.id) == 1


@pytest.mark.parametrize("completed", [False, True])
async def test_archive_restore_preserves_status_and_is_idempotent(scenario, completed):
    factory, actor, service, batch, _ = scenario
    if completed:
        await service.complete(actor=actor, batch_id=batch.id)
    for _ in range(2):
        await service.set_archived(actor=actor, batch_id=batch.id, archived=True)
    for _ in range(2):
        restored = await service.set_archived(actor=actor, batch_id=batch.id, archived=False)
    assert restored.archived_at is None
    assert restored.status == (BatchStatus.COMPLETED if completed else BatchStatus.IN_PRODUCTION)
    async with factory() as session:
        actions = list(
            await session.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == str(batch.id))
            )
        )
    assert actions.count("batch.archived") == actions.count("batch.restored") == 1
