"""Batch shipment routes over HTTP with a signed-in manager."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db import models as m
from app.db.enums import UserRole

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import CreateBatch, CreateShipment, PackUnits

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(name="manager", autouse=True)
async def fx_manager(sign_in: SignIn) -> m.User:
    return await sign_in(UserRole.MANAGER)


async def test_create_shipment_returns_open_shipment(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.post(
        f"/api/batches/{batch.id}/shipments",
        json={"comment": "Pick up on Thursday"},
    )

    body = response.json()
    assert (
        response.status_code,
        body["batchId"],
        body["status"],
        body["comment"],
        body["quantity"],
        isinstance(body["number"], int),
    ) == (201, str(batch.id), "open", "Pick up on Thursday", 0, True)


async def test_create_shipment_writes_audit_entry(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    manager: m.User,
) -> None:
    batch = await create_batch()

    response = await client.post(f"/api/batches/{batch.id}/shipments", json={})

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.target_id == response.json()["id"]))
    assert entry is not None
    assert (entry.action, entry.actor_id, entry.details) == (
        "batch_shipment.created",
        manager.id,
        {"batch_id": str(batch.id)},
    )


async def test_list_shipments_filters_by_status(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    completed = await create_shipment(batch, batch.first_dev_eui, completed=True)
    await create_shipment(batch)

    response = await client.get(f"/api/batches/{batch.id}/shipments", params={"statusIn": "completed"})

    body = response.json()
    assert ([item["id"] for item in body["items"]], body["total"]) == ([str(completed.id)], 1)


async def test_list_shipments_of_unknown_batch_is_not_found(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get(f"/api/batches/{uuid4()}/shipments")

    assert response.status_code == 404


async def test_get_shipment_returns_quantity(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, batch.last_dev_eui)

    response = await client.get(f"/api/batches/{batch.id}/shipments/{shipment.id}")

    assert (response.status_code, response.json()["quantity"]) == (200, 2)


async def test_update_shipment_changes_comment(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    shipment = await create_shipment(batch)

    response = await client.patch(
        f"/api/batches/{batch.id}/shipments/{shipment.id}",
        json={"expectedUpdatedAt": shipment.updated_at.isoformat(), "comment": "Thursday"},
    )

    assert (response.status_code, response.json()["comment"]) == (200, "Thursday")


async def test_complete_shipment_returns_completed_shipment(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    response = await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/complete",
        json={"expectedQuantity": 1},
    )

    body = response.json()
    assert (response.status_code, body["status"], body["completedAt"] is not None, body["quantity"]) == (
        200,
        "completed",
        True,
        1,
    )


async def test_complete_shipment_names_who_shipped_it(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
    manager: m.User,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    response = await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/complete",
        json={"expectedQuantity": 1},
    )

    assert response.json()["completedBy"]["id"] == str(manager.id)


async def test_complete_shipment_writes_audit_entry_with_quantity(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    await client.post(f"/api/batches/{batch.id}/shipments/{shipment.id}/complete", json={"expectedQuantity": 1})

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.action == "batch_shipment.completed"))
    assert entry is not None
    assert (entry.target_id, entry.details) == (str(shipment.id), {"batch_id": str(batch.id), "quantity": 1})


async def test_complete_empty_shipment_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    shipment = await create_shipment(batch)

    response = await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/complete",
        json={"expectedQuantity": 1},
    )

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_shipment_empty"})


async def test_complete_shipment_whose_units_changed_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, batch.last_dev_eui)

    response = await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/complete",
        json={"expectedQuantity": 1},
    )

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_shipment_quantity_changed"})


async def test_void_shipment_returns_voided_shipment(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    shipment = await create_shipment(batch)

    response = await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/void",
        json={"reason": " Cancelled "},
    )

    body = response.json()
    assert (response.status_code, body["status"], body["voidReason"]) == (200, "voided", "Cancelled")


async def test_completed_shipment_lists_its_units_as_shipped(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    await create_shipment(batch, batch.first_dev_eui, completed=True)

    response = await client.get("/api/kg/units", params={"stateIn": "shipped"})

    assert [item["devEui"] for item in response.json()["items"]] == [batch.first_dev_eui]
