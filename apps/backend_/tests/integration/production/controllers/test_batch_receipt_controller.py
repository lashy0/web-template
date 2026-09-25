"""Batch receipt routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.db import models as m
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import CreateBatch, CreatePrefix, CreateReceipt

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(name="administrator", autouse=True)
async def fx_administrator(sign_in: SignIn) -> m.User:
    return await sign_in()


async def test_list_receipts_returns_receipts_of_the_batch(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    prefix = await create_prefix()
    batch = await create_batch(prefix)
    receipt = await create_receipt(batch)
    await create_receipt(await create_batch(prefix))

    response = await client.get(f"/batches/{batch.id}/receipts")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(receipt.id)]


async def test_list_receipts_filters_out_voided(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    voided = await create_receipt(batch)
    current = await create_receipt(batch)
    await client.post(f"/batches/{batch.id}/receipts/{voided.id}/void", json={"reason": "Counted twice"})

    response = await client.get(f"/batches/{batch.id}/receipts", params={"voided": "false"})

    assert [item["id"] for item in response.json()["items"]] == [str(current.id)]


async def test_list_receipts_of_missing_batch_is_not_found(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get(f"/batches/{uuid4()}/receipts")

    assert response.status_code == 404


async def test_get_receipt_returns_it(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch, 2)

    response = await client.get(f"/batches/{batch.id}/receipts/{receipt.id}")

    assert (response.status_code, response.json()["quantity"]) == (200, 2)


async def test_create_receipt_returns_it_with_creator(
    client: AsyncTestClient[Litestar],
    administrator: m.User,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.post(f"/batches/{batch.id}/receipts", json={"quantity": 2, "comment": "Shift 1"})

    assert response.status_code == 201
    assert (response.json()["quantity"], response.json()["createdBy"]["id"]) == (2, str(administrator.id))


async def test_create_receipt_updates_batch_received_qty(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch(planned_qty=5)

    await client.post(f"/batches/{batch.id}/receipts", json={"quantity": 2})

    assert (await client.get(f"/batches/{batch.id}")).json()["receivedQty"] == 2


async def test_create_receipt_beyond_planned_qty_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch(planned_qty=3)

    response = await client.post(f"/batches/{batch.id}/receipts", json={"quantity": 4})

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_receipt_quantity_exceeded"})


async def test_create_receipt_without_units_is_bad_request(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.post(f"/batches/{batch.id}/receipts", json={"quantity": 0})

    assert response.status_code == 400


async def test_create_receipt_writes_audit_entry(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.post(f"/batches/{batch.id}/receipts", json={"quantity": 1})

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.target_id == response.json()["id"]))
    assert entry is not None
    assert (entry.action, entry.details) == ("batch_receipt.created", {"batch_id": str(batch.id), "quantity": 1})


async def test_update_receipt_changes_given_fields(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)

    response = await client.patch(f"/batches/{batch.id}/receipts/{receipt.id}", json={"quantity": 2})

    assert (response.status_code, response.json()["quantity"]) == (200, 2)


async def test_update_receipt_after_edit_window_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)

    async with unit_of_work(session):
        await session.execute(
            update(m.BatchReceipt)
            .where(m.BatchReceipt.id == receipt.id)
            .values(created_at=datetime.now(UTC) - timedelta(hours=2))
        )

    response = await client.patch(f"/batches/{batch.id}/receipts/{receipt.id}", json={"comment": "Late"})

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_receipt_edit_window_expired"})


async def test_void_receipt_keeps_it_with_reason(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)

    response = await client.post(
        f"/batches/{batch.id}/receipts/{receipt.id}/void",
        json={"reason": "  Counted twice  "},
    )

    assert response.status_code == 200
    assert response.json()["voidReason"] == "Counted twice"
    assert response.json()["voidedAt"] is not None


async def test_void_voided_receipt_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)
    path = f"/batches/{batch.id}/receipts/{receipt.id}/void"
    await client.post(path, json={"reason": "Counted twice"})

    response = await client.post(path, json={"reason": "Again"})

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_receipt_voided"})


async def test_delete_batch_with_receipt_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    await create_receipt(batch)

    response = await client.delete(f"/batches/{batch.id}")

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "batch_in_use"})
