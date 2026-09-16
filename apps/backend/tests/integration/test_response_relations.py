from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, event
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import Role
from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.domains.equipment.pak.model import PakDevice, PakDeviceKind
from app.domains.identity.users.model import User
from app.domains.production.batches.model import Batch
from app.domains.production.batches.presentation import batch_response, receipt_response
from app.domains.production.batches.repository import BatchRepository
from app.domains.production.kg.model import KgDevEuiPrefix, KgUnit, KgVersion
from app.domains.production.kg.router import _kg_response
from app.domains.production.kg.schemas import KgCurrentState
from app.domains.production.receipts.repository import ReceiptRepository as BatchReceiptRepository
from app.domains.production.shipments.model import BatchShipmentItem
from app.domains.production.shipments.repository import (
    ShipmentRepository as BatchShipmentRepository,
)
from app.domains.quality.checks.model import Check
from app.domains.quality.checks.router import _response as check_response
from app.domains.quality.defects.model import DefectGroup, DefectType
from app.domains.quality.defects.repository import DefectGroupRepository
from app.domains.quality.defects.router import _group_response
from app.domains.quality.verification.model import VerificationSession
from app.domains.quality.verification.router import _session_response

pytestmark = pytest.mark.integration


def _batch_response(batch: Batch):
    return batch_response(batch, can_delete=True, job=None)


_receipt_response = receipt_response


async def make_batch(session: AsyncSession) -> Batch:
    prefix = KgDevEuiPrefix(prefix=uuid4().hex[:10], short_code=uuid4().hex[:8])
    version = KgVersion(code=uuid4().hex, name="Archived version", archived_at=datetime.now(UTC))
    author = User(identity_id=uuid4(), name="Author", role=Role.MANAGER)
    session.add_all([prefix, version, author])
    await session.flush()
    return await BatchRepository(session).create(
        name="Production",
        description=None,
        dev_eui_prefix=prefix.prefix,
        kg_version_id=version.id,
        planned_qty=10,
        day_plan_qty=2,
        created_by_user_id=author.id,
        activation_type=ActivationType.OTAA,
        lorawan_version=LoRaWanVersion.V1_1,
        join_eui="0123456789abcdef",
    )


async def test_batch_and_receipt_mutations_load_authors_before_detach(db_session: AsyncSession):
    batch = await make_batch(db_session)
    assert _batch_response(batch).created_by_user.name == "Author"
    assert _batch_response(batch).kg_version.name == "Archived version"
    receipt = await BatchReceiptRepository(db_session).create(
        batch_id=batch.id,
        quantity=2,
        comment=None,
        created_by_user_id=batch.created_by_user_id,
    )
    shipment = await BatchShipmentRepository(db_session).create(
        batch_id=batch.id,
        comment=None,
        created_by_user_id=batch.created_by_user_id,
    )
    await BatchRepository(db_session).update_details(batch, updates={"name": "Updated"})
    await BatchReceiptRepository(db_session).update_details(receipt, updates={"quantity": 3})
    db_session.expunge_all()
    assert _batch_response(batch).created_by_user.name == "Author"
    assert _receipt_response(receipt).created_by_user.name == "Author"
    assert shipment.created_by_user.name == "Author"
    await db_session.execute(delete(User).where(User.id == batch.created_by_user_id))
    await db_session.flush()
    batch = await BatchRepository(db_session).get_by_id(batch.id)
    receipt = await BatchReceiptRepository(db_session).get_by_id(receipt.id)
    shipment = await BatchShipmentRepository(db_session).get_by_id(shipment.id)
    db_session.expunge_all()
    assert _batch_response(batch).created_by_user is None
    assert _receipt_response(receipt).created_by_user is None
    assert shipment.created_by_user is None


async def test_summaries_survive_detach_and_archived_relations(db_session: AsyncSession):
    batch = await make_batch(db_session)
    kg = KgUnit(
        dev_eui=uuid4().hex[:16],
        short_id=uuid4().hex[:20],
        batch_id=batch.id,
        state="REGISTERED",
    )
    group = DefectGroup(code=uuid4().hex, name="Archived group", archived_at=datetime.now(UTC))
    pak = PakDevice(
        code=uuid4().hex,
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id=uuid4().hex,
        encrypted_access_key="secret",
        archived_at=datetime.now(UTC),
    )
    db_session.add_all([kg, group, pak])
    await db_session.flush()
    check = Check(test_name=uuid4().hex, test_label="Test", defect_group_id=group.id)
    verification = VerificationSession(
        kg_dev_eui=kg.dev_eui, pak_id=pak.id, slot_no=1, firmware_version="1.0", total_steps=1
    )
    db_session.add_all([check, verification])
    await db_session.flush()
    keys = (kg.dev_eui, check.id, verification.id)
    db_session.expunge_all()
    kg = await db_session.get(KgUnit, keys[0])
    check = await db_session.get(Check, keys[1])
    verification = await db_session.get(VerificationSession, keys[2])
    db_session.expunge_all()
    assert _kg_response(kg, current_state=KgCurrentState.REGISTERED).batch.name == "Production"
    assert check_response(check).defect_group.name == "Archived group"
    assert _session_response(verification).pak.code == pak.code
    assert "encrypted_access_key" not in _session_response(verification).model_dump()["pak"]


async def test_group_single_and_list_counts_agree_after_mutations(db_session: AsyncSession):
    repo = DefectGroupRepository(db_session)
    group = await repo.create(code=uuid4().hex, name="Group", description=None)
    assert _group_response(group).types_count == 0
    group_id = group.id
    db_session.add_all(
        [
            DefectType(group_id=group_id, code=uuid4().hex, name="Active", description="Active"),
            DefectType(
                group_id=group_id,
                code=uuid4().hex,
                name="Archived",
                description="Archived",
                archived_at=datetime.now(UTC),
            ),
        ]
    )
    await db_session.flush()
    db_session.expunge_all()
    group = await repo.get_by_id(group_id)
    for archived_at in (datetime.now(UTC), None):
        await repo.update_details(group, updates={"name": "Updated"})
        await repo.update_archived(group, archived_at=archived_at)
        response = _group_response(group)
        items, _ = await repo.search(
            q=group.code,
            archived=archived_at is not None,
            page=1,
            page_size=10,
            sort="code",
            order="asc",
        )
        assert (response.active_types_count, response.types_count) == (1, 2)
        assert items[0][1:] == (1, 2)
    db_session.expunge_all()
    assert _group_response(group).types_count == 2


async def test_shipment_counts_are_scoped_and_use_one_query(db_session: AsyncSession):
    batch = await make_batch(db_session)
    other_batch = await make_batch(db_session)
    repo = BatchShipmentRepository(db_session)
    shipments = [
        await repo.create(batch_id=batch.id, comment=None, created_by_user_id=None)
        for _ in range(3)
    ]
    other = await repo.create(batch_id=other_batch.id, comment=None, created_by_user_id=None)
    for shipment in (shipments[0], shipments[0], shipments[1], other):
        kg = KgUnit(
            dev_eui=uuid4().hex[:16],
            short_id=uuid4().hex[:20],
            batch_id=shipment.batch_id,
            state="REGISTERED",
        )
        db_session.add(kg)
        await db_session.flush()
        db_session.add(BatchShipmentItem(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui))
    await db_session.flush()
    await repo.void(shipments[1], voided_at=datetime.now(UTC), reason="Duplicate")
    statements = []

    def record(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = db_session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        counts = await repo.count_items_by_batch(batch.id)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert len(statements) == 1
    assert counts == {shipments[0].id: 2, shipments[1].id: 1}
    assert counts.get(shipments[2].id, 0) == 0
    assert other.id not in counts
