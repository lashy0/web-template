import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import AuditService
from app.modules.batch.exceptions import BatchArchivedError, BatchEditNotAllowedError
from app.modules.batch.models import Batch, BatchStatus
from app.modules.batch.repositories import BatchRepository
from app.modules.batch.routers.common import _batch_response
from app.modules.batch.services import BatchManagementService
from app.modules.kg.models import KgDevEuiPrefix
from app.modules.production_order.exceptions import (
    ProductionOrderArchivedError,
    ProductionOrderCannotBeDeletedError,
    ProductionOrderNotFoundError,
)
from app.modules.production_order.models import ProductionOrder
from app.modules.production_order.repository import ProductionOrderRepository
from app.modules.production_order.service import ProductionOrderService
from app.modules.production_order.services import ProductionOrderManagementService
from app.modules.users.models import User

pytestmark = pytest.mark.integration


async def test_management_commits_crud_and_returns_loaded_models(scenario):
    factory, actor, _, _, _, _, _ = scenario
    service = ProductionOrderManagementService(factory)
    name = f"Managed-{uuid4()}"
    item = await service.create(actor=actor, name=name, description=None)
    assert (item.name, item.description, item.archived_at) == (name, None, None)
    assert item.created_at is not None and item.updated_at is not None
    assert (await service.get(item.id)).name == name
    assert await service.get(uuid4()) is None
    assert await service.get_totals(item.id) == (0, 0)
    items, total = await service.list(
        q=name,
        archived=False,
        page=1,
        page_size=25,
        sort="created_at",
        order="desc",
    )
    assert total == 1 and items[0][0].id == item.id and items[0][1:] == (0, 0)
    updated = await service.update(
        actor=actor, order_id=item.id, updates={"description": "Updated"}
    )
    assert updated.description == "Updated" and updated.updated_at is not None
    archived = await service.set_archived(actor=actor, order_id=item.id, archived=True)
    assert archived.archived_at is not None and archived.updated_at is not None
    await service.delete(actor=actor, order_id=item.id)
    assert await service.get(item.id) is None
    async with factory() as session:
        actions = list(
            await session.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == str(item.id))
            )
        )
        assert set(actions) == {
            "production_order.created",
            "production_order.updated",
            "production_order.archived",
            "production_order.deleted",
        }


@pytest.mark.parametrize("operation", ["create", "update", "archive", "delete"])
async def test_management_rolls_back_on_audit_failure(scenario, monkeypatch, operation):
    factory, actor, _, _, first, _, _ = scenario
    service = ProductionOrderManagementService(factory)
    name = f"Failed-{uuid4()}"
    original = await service.get(first)

    async def fail(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditService, "record", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        if operation == "create":
            await service.create(actor=actor, name=name, description=None)
        elif operation == "update":
            await service.update(actor=actor, order_id=first, updates={"name": name})
        elif operation == "archive":
            await service.set_archived(actor=actor, order_id=first, archived=True)
        else:
            await service.delete(actor=actor, order_id=first)
    current = await service.get(first)
    assert current.name == original.name
    assert current.archived_at is None
    assert current.updated_at == original.updated_at
    async with factory() as session:
        assert (
            await session.scalar(select(ProductionOrder).where(ProductionOrder.name == name))
            is None
        )


@pytest.fixture
async def scenario(database_session_factory):
    factory = database_session_factory
    actor = CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.MANAGER
    )
    prefix = uuid4().hex[:10]
    async with factory() as session, session.begin():
        session.add(
            User(id=actor.user_id, identity_id=actor.identity_id, role=actor.role, name="Orders")
        )
        session.add(KgDevEuiPrefix(prefix=prefix, short_code=prefix))
        service = ProductionOrderService(session)
        first = await service.create(actor=actor, name=f"Order-{uuid4()}", description="First")
        second = await service.create(actor=actor, name=f"Order-{uuid4()}", description=None)
    batches = BatchManagementService(factory)
    batch = await batches.create(
        actor=actor,
        name="Batch",
        description=None,
        dev_eui_prefix=prefix,
        planned_qty=2,
        day_plan_qty=1,
    )
    return factory, actor, batches, batch, first.id, second.id, prefix


@pytest.mark.parametrize("release", ["detach", "move", "delete"])
@pytest.mark.parametrize("archived_order", [False, True])
async def test_order_deletion_depends_only_on_current_membership(scenario, release, archived_order):
    factory, actor, batches, batch, first, second, _ = scenario
    await batches.assign_production_order(actor=actor, batch_id=batch.id, production_order_id=first)
    await batches.set_archived(actor=actor, batch_id=batch.id, archived=True)
    async with factory() as session, session.begin():
        service = ProductionOrderService(session)
        await service.set_archived(first, actor=actor, archived=archived_order)
        with pytest.raises(ProductionOrderCannotBeDeletedError):
            await service.delete(first, actor=actor)
    await batches.set_archived(actor=actor, batch_id=batch.id, archived=False)
    if release == "delete":
        await batches.delete(actor=actor, batch_id=batch.id)
    else:
        await batches.assign_production_order(
            actor=actor,
            batch_id=batch.id,
            production_order_id=second if release == "move" else None,
        )
    async with factory() as session, session.begin():
        await ProductionOrderService(session).delete(first, actor=actor)
        assert await session.get(ProductionOrder, first) is None
        actions = list(
            await session.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == str(first))
            )
        )
        assert "production_order.created" in actions
        assert "production_order.deleted" in actions


async def test_membership_history_aggregates_and_detached_response(scenario):
    factory, actor, batches, batch, first, second, _ = scenario
    assigned = await batches.assign_production_order(
        actor=actor, batch_id=batch.id, production_order_id=first
    )
    assert _batch_response(assigned).production_order.id == first
    async with factory() as session:
        response = await ProductionOrderRepository(session).get_totals(first)
        assert response == (1, 2)
    await batches.set_archived(actor=actor, batch_id=batch.id, archived=True)
    async with factory() as session:
        assert (await ProductionOrderRepository(session).get_totals(first))[1] == 2
    with pytest.raises(BatchArchivedError):
        await batches.assign_production_order(
            actor=actor, batch_id=batch.id, production_order_id=None
        )
    await batches.set_archived(actor=actor, batch_id=batch.id, archived=False)
    await batches.assign_production_order(
        actor=actor, batch_id=batch.id, production_order_id=second
    )
    await batches.assign_production_order(actor=actor, batch_id=batch.id, production_order_id=None)
    await batches.delete(actor=actor, batch_id=batch.id)
    for order_id in (first, second):
        async with factory() as session, session.begin():
            response = await ProductionOrderRepository(session).get_totals(order_id)
            assert response == (0, 0)
            await ProductionOrderService(session).delete(order_id, actor=actor)
            assert await session.get(ProductionOrder, order_id) is None
    async with factory() as session:
        events = list(
            await session.scalars(
                select(AuditEvent).where(
                    AuditEvent.entity_id == str(batch.id),
                    AuditEvent.action == "batch.production_order_changed",
                )
            )
        )
        assert len(events) == 3
        assert events[0].old_data == {"production_order_id": None}


async def test_archived_order_noop_detach_and_reuse(scenario):
    factory, actor, batches, batch, first, second, _ = scenario
    await batches.assign_production_order(actor=actor, batch_id=batch.id, production_order_id=first)
    async with factory() as session, session.begin():
        service = ProductionOrderService(session)
        await service.set_archived(first, actor=actor, archived=True)
        await service.set_archived(first, actor=actor, archived=True)
        await service.update(first, actor=actor, updates={"description": "Archived"})
    await batches.assign_production_order(actor=actor, batch_id=batch.id, production_order_id=first)
    await batches.assign_production_order(actor=actor, batch_id=batch.id, production_order_id=None)
    with pytest.raises(ProductionOrderArchivedError):
        await batches.assign_production_order(
            actor=actor, batch_id=batch.id, production_order_id=first
        )
    async with factory() as session, session.begin():
        service = ProductionOrderService(session)
        await service.set_archived(first, actor=actor, archived=False)
        await service.set_archived(second, actor=actor, archived=True)
        await service.delete(second, actor=actor)
    await batches.assign_production_order(actor=actor, batch_id=batch.id, production_order_id=first)
    async with factory() as session:
        events = list(
            await session.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == str(first))
            )
        )
        assert events.count("production_order.archived") == 1


async def test_manager_can_reassign_old_foreign_completed_batch(scenario):
    factory, actor, batches, batch, first, _, _ = scenario
    async with factory() as session, session.begin():
        item = await session.get(Batch, batch.id)
        item.created_at = datetime.now(UTC) - timedelta(days=10)
        item.created_by_user_id = None
        item.status = BatchStatus.COMPLETED
    result = await batches.assign_production_order(
        actor=actor, batch_id=batch.id, production_order_id=first
    )
    assert result.production_order_id == first
    with pytest.raises(BatchEditNotAllowedError):
        await batches.update(actor=actor, batch_id=batch.id, updates={"name": "Changed"})


@pytest.mark.parametrize("creating", [False, True])
async def test_audit_failure_rolls_back_membership(scenario, monkeypatch, creating):
    factory, actor, batches, batch, first, _, prefix = scenario

    async def fail(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditService, "record", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        if creating:
            await batches.create(
                actor=actor,
                name="Failed",
                description=None,
                dev_eui_prefix=prefix,
                planned_qty=1,
                day_plan_qty=1,
                production_order_id=first,
            )
        else:
            await batches.assign_production_order(
                actor=actor, batch_id=batch.id, production_order_id=first
            )
    async with factory() as session:
        response = await ProductionOrderRepository(session).get_totals(first)
        assert response[0] == 0
        assert (await session.get(Batch, batch.id)).production_order_id is None


async def test_create_with_order_and_missing_order(scenario):
    factory, actor, batches, _, first, _, prefix = scenario
    with pytest.raises(ProductionOrderNotFoundError):
        await batches.create(
            actor=actor,
            name="Missing",
            description=None,
            dev_eui_prefix=prefix,
            planned_qty=1,
            day_plan_qty=1,
            production_order_id=uuid4(),
        )
    batch = await batches.create(
        actor=actor,
        name="With order",
        description=None,
        dev_eui_prefix=prefix,
        planned_qty=3,
        day_plan_qty=1,
        production_order_id=first,
    )
    assert _batch_response(batch).production_order.id == first
    async with factory() as session:
        response = await ProductionOrderRepository(session).get_totals(first)
        assert response[1] == 3
        event = await session.scalar(
            select(AuditEvent).where(
                AuditEvent.entity_id == str(batch.id), AuditEvent.action == "batch.created"
            )
        )
        assert event.new_data["production_order_id"] == str(first)


async def test_fk_protects_current_membership(scenario):
    factory, actor, _, batch, first, _, _ = scenario
    async with factory() as session, session.begin():
        (await session.get(Batch, batch.id)).production_order_id = first
    async with factory() as session, session.begin():
        with pytest.raises(ProductionOrderCannotBeDeletedError):
            await ProductionOrderService(session).delete(first, actor=actor)
    with pytest.raises(IntegrityError):
        async with factory() as session, session.begin():
            await session.execute(delete(ProductionOrder).where(ProductionOrder.id == first))


@pytest.mark.parametrize("operation", ["archive", "delete"])
@pytest.mark.parametrize("assignment_first", [False, True])
async def test_concurrent_assignment_serializes_with_order_mutation(
    scenario, operation, assignment_first
):
    factory, actor, batches, batch, first, _, _ = scenario
    async with factory() as session, session.begin():
        service = ProductionOrderService(session)
        if assignment_first:
            # Hold the same locks as BatchService while the competing mutation starts.
            item = await BatchRepository(session).get_by_id(batch.id, for_update=True)
            await service.assign(first)
            item.production_order_id = first
            await session.flush()

            async def competing():
                async with factory() as other, other.begin():
                    target = ProductionOrderService(other)
                    if operation == "delete":
                        await target.delete(first, actor=actor)
                    else:
                        await target.set_archived(first, actor=actor, archived=True)
        else:
            if operation == "delete":
                await service.delete(first, actor=actor)
            else:
                await service.set_archived(first, actor=actor, archived=True)

            async def competing():
                return await batches.assign_production_order(
                    actor=actor, batch_id=batch.id, production_order_id=first
                )

        task = asyncio.create_task(competing())
        # Give the second connection an opportunity to reach the locked row.
        await asyncio.sleep(0.1)
        assert not task.done()
    if assignment_first and operation == "archive":
        await asyncio.wait_for(task, timeout=5)
    else:
        error = (
            ProductionOrderCannotBeDeletedError
            if assignment_first
            else ProductionOrderNotFoundError
            if operation == "delete"
            else ProductionOrderArchivedError
        )
        with pytest.raises(error):
            await asyncio.wait_for(task, timeout=5)
