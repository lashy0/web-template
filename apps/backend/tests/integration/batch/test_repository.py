from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch.models import BatchStatus
from app.modules.batch.repository import (
    BatchReceiptRepository,
    BatchRepository,
    BatchShipmentRepository,
)
from app.modules.kg.models import KgStatus
from app.modules.kg.repository import KgRepository


async def _batch(session: AsyncSession, *, name: str = "August production"):
    return await BatchRepository(session).create(
        name=name,
        description="Initial run",
        planned_qty=100,
        day_plan_qty=20,
        created_by_user_id=None,
    )


@pytest.mark.integration
async def test_batch_details_state_and_search_can_be_updated(db_session: AsyncSession) -> None:
    repository = BatchRepository(db_session)
    batch = await _batch(db_session)

    updated = await repository.update_details(batch, updates={"name": "September production"})
    completed = await repository.update_completed(updated, completed_at=datetime.now(UTC))
    await repository.update_archived(completed, archived_at=datetime.now(UTC))
    archived, total = await repository.search(
        q="September",
        status=BatchStatus.COMPLETED,
        archived=True,
        page=1,
        page_size=25,
        sort="name",
        order="asc",
    )

    assert completed.status is BatchStatus.COMPLETED
    assert total == 1
    assert [item.id for item in archived] == [batch.id]


@pytest.mark.integration
async def test_receipt_repository_excludes_voided_receipts_from_lists_and_totals(
    db_session: AsyncSession,
) -> None:
    batch = await _batch(db_session)
    repository = BatchReceiptRepository(db_session)
    active = await repository.create(
        batch_id=batch.id,
        quantity=10,
        comment="accepted",
        created_by_user_id=None,
    )
    voided = await repository.create(
        batch_id=batch.id,
        quantity=5,
        comment="duplicate",
        created_by_user_id=None,
    )
    await repository.void(voided, voided_at=datetime.now(UTC), reason="duplicate")

    active_receipts = await repository.list_by_batch(batch.id)
    all_receipts = await repository.list_by_batch(batch.id, include_voided=True)

    assert [receipt.id for receipt in active_receipts] == [active.id]
    assert {receipt.id for receipt in all_receipts} == {active.id, voided.id}
    assert await repository.get_total(batch.id) == 10
    assert await repository.exists_by_batch(batch.id)


@pytest.mark.integration
async def test_shipment_repository_tracks_items_completion_and_voiding(
    db_session: AsyncSession,
) -> None:
    batch = await _batch(db_session)
    kg_repository = KgRepository(db_session)
    shipment_repository = BatchShipmentRepository(db_session)
    kg = await kg_repository.create(dev_eui="a1b2c3d4e5f60708", batch_id=batch.id)
    await kg_repository.update_status(kg, status=KgStatus.PACKED)
    shipment = await shipment_repository.create(
        batch_id=batch.id,
        comment="outbound",
        created_by_user_id=None,
    )
    item = await shipment_repository.add_item(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui)

    assert await shipment_repository.count_items(shipment.id) == 1
    assert await shipment_repository.find_non_voided_by_kg(kg.dev_eui) is not None

    await shipment_repository.complete(shipment, completed_at=datetime.now(UTC))
    assert await shipment_repository.get_shipped_total(batch.id) == 1

    await shipment_repository.void(shipment, voided_at=datetime.now(UTC), reason="cancelled")
    assert await shipment_repository.get_shipped_total(batch.id) == 0
    assert await shipment_repository.list_by_batch(batch.id) == []
    assert (
        await shipment_repository.get_item(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui) is item
    )
