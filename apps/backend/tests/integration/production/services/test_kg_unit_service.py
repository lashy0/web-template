"""KG unit service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from advanced_alchemy.exceptions import NotFoundError

from app.db.enums import PakDeviceKind
from app.domain.production.schemas import KgTimelineEventKind
from app.domain.production.services import BatchShipmentService
from app.domain.quality.services import VerificationSessionService
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import models as m
    from app.domain.production.services import KgUnitService
    from tests.integration.production.conftest import CreateBatch, CreateShipment, PackUnits, VerifyUnit

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def test_get_timeline_of_new_unit_has_only_its_registration(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert [event.kind for event in timeline] == [KgTimelineEventKind.REGISTERED]


async def test_get_timeline_lists_otk_results_in_order(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": False})
    await verify_unit(batch.first_dev_eui, {"RF power": True})

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert [event.kind for event in timeline] == [
        KgTimelineEventKind.REGISTERED,
        KgTimelineEventKind.OTK_FAILED,
        KgTimelineEventKind.OTK_PASSED,
    ]


async def test_get_timeline_names_failed_checks_in_step_order(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"Power": True, "RF power": False, "Sensitivity": False})

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert timeline[-1].session is not None
    assert timeline[-1].session.failed_checks == ["RF power", "Sensitivity"]


async def test_get_timeline_names_the_firmware_of_each_otk(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": True})

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert timeline[-1].session is not None
    assert timeline[-1].session.firmware_version == "1.0.0"


async def test_get_timeline_shows_running_otk(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": True}, finish=False)

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert timeline[-1].kind is KgTimelineEventKind.OTK_RUNNING


async def test_get_timeline_shows_the_latest_otk_the_system_closed_at_its_last_report(
    session: AsyncSession,
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": False})
    await verify_unit(batch.first_dev_eui, {"RF power": True}, finish=False)
    closed = await _expire_running(session)

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert [event.kind for event in timeline] == [
        KgTimelineEventKind.REGISTERED,
        KgTimelineEventKind.OTK_FAILED,
        KgTimelineEventKind.OTK_INCOMPLETE,
    ]
    assert timeline[-1].at == closed[0].last_activity_at


async def test_get_timeline_leaves_out_an_otk_the_system_closed_before_a_later_one(
    session: AsyncSession,
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": True}, finish=False)
    await _expire_running(session)
    await verify_unit(batch.first_dev_eui, {"RF power": True})

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert [event.kind for event in timeline] == [
        KgTimelineEventKind.REGISTERED,
        KgTimelineEventKind.OTK_PASSED,
    ]


async def test_get_timeline_leaves_out_engineering_verifications(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": False}, kind=PakDeviceKind.ENGINEERING)

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert [event.kind for event in timeline] == [KgTimelineEventKind.REGISTERED]


async def test_get_timeline_shows_unit_in_open_shipment(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert [(event.kind, event.shipment and event.shipment.number) for event in timeline[1:]] == [
        (KgTimelineEventKind.PACKED, None),
        (KgTimelineEventKind.SHIPMENT_ADDED, shipment.number),
    ]


async def test_get_timeline_shows_shipping_and_its_voiding(
    kg_unit_service: KgUnitService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
    session: AsyncSession,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)

    async with unit_of_work(session), BatchShipmentService.new(session=session) as shipments:
        await shipments.void_shipment(batch.id, shipment.id, "Wrong recipient", voided_by_id=None)

    timeline = await kg_unit_service.get_timeline(batch.first_dev_eui)

    assert [event.kind for event in timeline[2:]] == [
        KgTimelineEventKind.SHIPPED,
        KgTimelineEventKind.SHIPMENT_VOIDED,
    ]


async def test_get_timeline_of_missing_unit_is_not_found(kg_unit_service: KgUnitService) -> None:
    with pytest.raises(NotFoundError):
        await kg_unit_service.get_timeline("ffffffffffffffff")


async def _expire_running(session: AsyncSession) -> list[m.VerificationSession]:
    """Close every running session as the background task does once the PAK stops reporting."""
    async with unit_of_work(session), VerificationSessionService.new(session=session) as sessions:
        return await sessions.expire_stale(idle_for=timedelta(0), limit=100)
