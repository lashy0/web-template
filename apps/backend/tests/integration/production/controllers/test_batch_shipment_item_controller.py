"""Routes for the KG units of a batch shipment over HTTP with a signed-in manager."""

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

    from tests.integration.conftest import OpenEventStream, SignIn
    from tests.integration.production.conftest import CreateBatch, CreateShipment, PackUnits

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(name="manager", autouse=True)
async def fx_manager(sign_in: SignIn) -> m.User:
    return await sign_in(UserRole.MANAGER)


async def test_add_units_reports_added_and_rejected(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch)

    response = await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/items",
        json={"codes": [batch.first_dev_eui.upper(), batch.last_dev_eui]},
    )

    body = response.json()
    assert (response.status_code, body["added"], body["rejected"], body["shipment"]["quantity"]) == (
        200,
        [batch.first_dev_eui],
        [{"code": batch.last_dev_eui, "reason": "batch_shipment_kg_not_packed", "shipmentNumber": None}],
        1,
    )


async def test_add_units_commits_and_announces_without_an_audit_entry(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch)

    async with open_event_stream() as events:
        response = await client.post(
            f"/api/batches/{batch.id}/shipments/{shipment.id}/items",
            json={"codes": [batch.first_dev_eui]},
        )
        event = await events.next_event()

    item = await session.scalar(select(m.BatchShipmentItem))
    entry = await session.scalar(select(m.AuditLog))
    assert item is not None
    assert (response.status_code, item.dev_eui, item.shipment_id, entry, event) == (
        200,
        batch.first_dev_eui,
        shipment.id,
        None,
        ("batch.changed", {"batchId": str(batch.id)}),
    )


async def test_add_units_to_completed_shipment_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)

    response = await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/items",
        json={"codes": [batch.last_dev_eui]},
    )

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_shipment_completed"})


async def test_add_packed_units_returns_shipment_with_them(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch)

    response = await client.post(f"/api/batches/{batch.id}/shipments/{shipment.id}/items/packed")

    assert (response.status_code, response.json()["quantity"]) == (200, 2)


async def test_list_items_returns_unit(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    response = await client.get(f"/api/batches/{batch.id}/shipments/{shipment.id}/items")

    item = response.json()["items"][0]
    assert (item["devEui"], item["shortId"]) == (batch.first_dev_eui, f"{batch.kg_prefix.short_code}-000001")


async def test_list_items_names_who_added_the_unit(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
    manager: m.User,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch)
    await client.post(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/items",
        json={"codes": [batch.first_dev_eui]},
    )

    response = await client.get(f"/api/batches/{batch.id}/shipments/{shipment.id}/items")

    assert response.json()["items"][0]["addedBy"]["id"] == str(manager.id)


async def test_list_items_of_unknown_shipment_is_not_found(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/api/batches/{batch.id}/shipments/{uuid4()}/items")

    assert response.status_code == 404


async def test_remove_unit_takes_it_out_of_shipment(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    response = await client.delete(
        f"/api/batches/{batch.id}/shipments/{shipment.id}/items/{batch.first_dev_eui.upper()}",
    )

    assert (response.status_code, await session.scalar(select(m.BatchShipmentItem))) == (204, None)
