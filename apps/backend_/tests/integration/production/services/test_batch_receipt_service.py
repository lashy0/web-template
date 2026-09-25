"""Batch receipt service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from advanced_alchemy.exceptions import NotFoundError
from sqlalchemy import update

from app.db import models as m
from app.domain.production.exceptions import (
    BatchArchivedError,
    BatchCompletedError,
    BatchInUseError,
    BatchReceiptEditWindowExpiredError,
    BatchReceiptQuantityExceededError,
    BatchReceiptVoidedError,
)
from app.domain.production.schemas import BatchReceiptCreate
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import BatchReceiptService, BatchService
    from tests.integration.production.conftest import CreateBatch, CreatePrefix, CreateReceipt

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def _age(session: AsyncSession, receipt: m.BatchReceipt, *, hours: int) -> None:
    async with unit_of_work(session):
        await session.execute(
            update(m.BatchReceipt)
            .where(m.BatchReceipt.id == receipt.id)
            .values(created_at=datetime.now(UTC) - timedelta(hours=hours))
        )


async def _received_qty(batch_service: BatchService, batch: m.Batch) -> int:
    batch_id = batch.id
    batch_service.repository.session.expire_all()

    return (await batch_service.get(batch_id)).received_qty


async def test_receipts_add_up_to_received_qty(
    batch_service: BatchService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(planned_qty=10)
    await create_receipt(batch, 3)
    await create_receipt(batch, 4)

    assert await _received_qty(batch_service, batch) == 7


async def test_voided_receipt_is_not_received(
    session: AsyncSession,
    batch_service: BatchService,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(planned_qty=10)
    receipt = await create_receipt(batch, 3)

    async with unit_of_work(session):
        await batch_receipt_service.void_receipt(batch.id, receipt.id, "Counted twice")

    assert await _received_qty(batch_service, batch) == 0


async def test_receipt_beyond_planned_qty_is_rejected(
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(planned_qty=5)
    await create_receipt(batch, 4)

    with pytest.raises(BatchReceiptQuantityExceededError, match="Only 1 of 5"):
        await create_receipt(batch, 2)


async def test_receipt_up_to_planned_qty_is_accepted(
    batch_service: BatchService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(planned_qty=5)
    await create_receipt(batch, 4)
    await create_receipt(batch, 1)

    assert await _received_qty(batch_service, batch) == 5


async def test_voided_receipt_frees_its_quantity(
    session: AsyncSession,
    batch_service: BatchService,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(planned_qty=5)
    receipt = await create_receipt(batch, 5)

    async with unit_of_work(session):
        await batch_receipt_service.void_receipt(batch.id, receipt.id, "Wrong batch")

    await create_receipt(batch, 5)

    assert await _received_qty(batch_service, batch) == 5


async def test_increasing_receipt_beyond_planned_qty_is_rejected(
    session: AsyncSession,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(planned_qty=5)
    receipt = await create_receipt(batch, 2)
    await create_receipt(batch, 2)

    with pytest.raises(BatchReceiptQuantityExceededError):
        async with unit_of_work(session):
            await batch_receipt_service.update_receipt(batch.id, receipt.id, {"quantity": 4})


async def test_increasing_receipt_within_planned_qty_is_accepted(
    session: AsyncSession,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(planned_qty=5)
    receipt = await create_receipt(batch, 2)
    await create_receipt(batch, 2)

    async with unit_of_work(session):
        updated = await batch_receipt_service.update_receipt(batch.id, receipt.id, {"quantity": 3})

    assert updated.quantity == 3


async def test_receipt_for_completed_batch_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await batch_service.complete_batch(batch.id)

    with pytest.raises(BatchCompletedError):
        await create_receipt(batch)


async def test_receipt_for_archived_batch_is_rejected(
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch(archived=True)

    with pytest.raises(BatchArchivedError):
        await create_receipt(batch)


async def test_receipt_of_another_batch_is_not_found(
    session: AsyncSession,
    batch_receipt_service: BatchReceiptService,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    prefix = await create_prefix()
    receipt = await create_receipt(await create_batch(prefix))
    other = await create_batch(prefix)

    with pytest.raises(NotFoundError, match="Receipt not found"):
        async with unit_of_work(session):
            await batch_receipt_service.void_receipt(other.id, receipt.id, "Wrong batch")


async def test_update_receipt_after_edit_window_is_rejected(
    session: AsyncSession,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)
    await _age(session, receipt, hours=2)

    with pytest.raises(BatchReceiptEditWindowExpiredError):
        async with unit_of_work(session):
            await batch_receipt_service.update_receipt(batch.id, receipt.id, {"comment": "Late"})


async def test_void_receipt_after_edit_window_is_rejected(
    session: AsyncSession,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)
    await _age(session, receipt, hours=2)

    with pytest.raises(BatchReceiptEditWindowExpiredError):
        async with unit_of_work(session):
            await batch_receipt_service.void_receipt(batch.id, receipt.id, "Late")


async def test_voided_receipt_cannot_be_changed(
    session: AsyncSession,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)

    async with unit_of_work(session):
        await batch_receipt_service.void_receipt(batch.id, receipt.id, "Counted twice")

    with pytest.raises(BatchReceiptVoidedError):
        async with unit_of_work(session):
            await batch_receipt_service.update_receipt(batch.id, receipt.id, {"quantity": 2})


async def test_receipt_of_archived_batch_cannot_be_voided(
    session: AsyncSession,
    batch_service: BatchService,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)

    async with unit_of_work(session):
        await batch_service.set_archived(batch.id, archived=True)

    with pytest.raises(BatchArchivedError):
        async with unit_of_work(session):
            await batch_receipt_service.void_receipt(batch.id, receipt.id, "Archived")


async def test_delete_batch_with_voided_receipt_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
    create_receipt: CreateReceipt,
) -> None:
    batch = await create_batch()
    receipt = await create_receipt(batch)

    async with unit_of_work(session):
        await batch_receipt_service.void_receipt(batch.id, receipt.id, "Counted twice")

    with pytest.raises(BatchInUseError):
        async with unit_of_work(session):
            await batch_service.delete_batch(batch.id)


async def test_new_batch_has_nothing_received(
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    assert batch.received_qty == 0


async def test_create_receipt_records_creator(
    session: AsyncSession,
    batch_receipt_service: BatchReceiptService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        receipt = await batch_receipt_service.create_receipt(
            batch.id,
            BatchReceiptCreate(quantity=1, comment="Shift 1"),
            created_by_id=None,
        )

    assert (receipt.quantity, receipt.comment, receipt.created_by) == (1, "Shift 1", None)
