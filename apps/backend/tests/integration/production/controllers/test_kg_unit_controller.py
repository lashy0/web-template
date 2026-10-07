"""Read-only KG unit routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import update

from app.db import models as m
from app.db.enums import KgState, PakDeviceKind
from app.lib.lorawan import ActivationType, LoRaWanVersion, generate_credentials
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import BatchShipmentService
    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import (
        CreateBatch,
        CreatePrefix,
        CreateShipment,
        CreateVersion,
        PackUnits,
        VerifyUnit,
    )

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _administrator(sign_in: SignIn) -> None:
    await sign_in()


async def test_list_kg_units_filters_by_batch(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5")
    await create_batch(prefix, planned_qty=1)
    batch = await create_batch(prefix, planned_qty=2)

    response = await client.get("/api/kg/units", params={"batchIdIn": str(batch.id)})

    assert [item["devEui"] for item in response.json()["items"]] == ["a1b2c3d4e5000002", "a1b2c3d4e5000003"]


async def test_list_kg_units_filters_by_state(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit).where(m.KgUnit.dev_eui == batch.last_dev_eui).values(state=KgState.SCRAPPED)
        )

    response = await client.get("/api/kg/units", params={"stateIn": "scrapped"})

    assert [item["devEui"] for item in response.json()["items"]] == [batch.last_dev_eui]


async def test_list_kg_units_filters_by_last_verification_date(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()
    verified_at = {
        batch.first_dev_eui: datetime(2026, 9, 29, 12, tzinfo=UTC),
        batch.last_dev_eui: datetime(2026, 9, 30, 12, tzinfo=UTC),
    }
    async with unit_of_work(session):
        for dev_eui, moment in verified_at.items():
            await session.execute(
                update(m.KgUnit).where(m.KgUnit.dev_eui == dev_eui).values(last_verification_at=moment)
            )

    response = await client.get(
        "/api/kg/units",
        params={
            "batchIdIn": str(batch.id),
            "lastVerificationAfter": "2026-09-30T00:00:00Z",
            "lastVerificationBefore": "2026-10-01T00:00:00Z",
        },
    )

    # The unit never verified has no date and is left out too.
    assert [item["devEui"] for item in response.json()["items"]] == [batch.last_dev_eui]


async def test_list_kg_units_finds_short_id(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5", "ab1")
    await create_batch(prefix, planned_qty=3)

    response = await client.get("/api/kg/units", params={"searchString": "AB1-000002"})

    assert [item["shortId"] for item in response.json()["items"]] == ["ab1-000002"]


async def test_get_kg_unit_accepts_upper_case_dev_eui(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui.upper()}")

    assert (response.status_code, response.json()["batch"]) == (200, {"id": str(batch.id), "name": batch.name})


async def test_get_kg_unit_with_malformed_dev_eui_is_bad_request(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/api/kg/units/not-a-dev-eui")

    assert response.status_code == 400


async def test_get_missing_kg_unit_is_not_found(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/api/kg/units/ffffffffffffffff")

    assert response.status_code == 404


async def test_get_kg_unit_shows_batch_lorawan_settings(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui}")

    assert (response.json()["activationType"], response.json()["lorawanVersion"]) == ("otaa", "1.0")


async def test_get_kg_unit_shows_batch_kg_version(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    create_version: CreateVersion,
) -> None:
    version = await create_version("kg-2")
    batch = await create_batch(kg_version_id=version.id)

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui}")

    assert response.json()["kgVersion"] == {"id": str(version.id), "code": "kg-2", "name": "Version kg-2"}


async def test_get_kg_unit_timeline_starts_with_its_registration(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui.upper()}/timeline")

    assert (response.status_code, [event["kind"] for event in response.json()]) == (200, ["registered"])


async def test_list_kg_units_filters_by_otk_running_now_whatever_the_result(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": False})
    running = await verify_unit(batch.first_dev_eui, {"RF power": True}, finish=False)
    # An engineering PAK does not verify for OTK, so its running session is not shown.
    await verify_unit(batch.last_dev_eui, {"RF power": True}, kind=PakDeviceKind.ENGINEERING, finish=False)

    response = await client.get("/api/kg/units", params={"batchIdIn": str(batch.id), "otkIn": "running"})

    assert [(item["devEui"], item["otkStatus"], item["runningOtk"]) for item in response.json()["items"]] == [
        (
            batch.first_dev_eui,
            "failed",
            {"id": str(running.id), "pak": {"id": str(running.pak_id), "code": running.pak.code}, "slotNo": 1},
        ),
    ]


async def test_list_kg_units_otk_filter_adds_up_results_and_running(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": False})
    await verify_unit(batch.first_dev_eui, {"RF power": True}, finish=False)
    await verify_unit(batch.last_dev_eui, {"RF power": False})

    response = await client.get(
        "/api/kg/units",
        params={"batchIdIn": str(batch.id), "otkIn": ["running", "failed"]},
    )

    assert [item["devEui"] for item in response.json()["items"]] == [batch.first_dev_eui, batch.last_dev_eui]
    assert response.json()["total"] == 2


async def test_list_kg_units_otk_running_filter_excludes_finished_sessions(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    verify_unit: VerifyUnit,
) -> None:
    batch = await create_batch()
    await verify_unit(batch.first_dev_eui, {"RF power": True})

    response = await client.get("/api/kg/units", params={"batchIdIn": str(batch.id), "otkIn": "running"})

    assert response.status_code == 200
    assert (response.json()["items"], response.json()["total"]) == ([], 0)


async def test_get_kg_unit_shows_the_shipment_that_shipped_it(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui}")

    assert response.json()["shipment"]["number"] == shipment.number


async def test_get_kg_unit_in_an_open_shipment_shows_no_shipment(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    await create_shipment(batch, batch.first_dev_eui)

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui}")

    assert response.json()["shipment"] is None


@pytest.mark.parametrize("bounds", [("shippedAfter",), ("shippedBefore",), ("shippedAfter", "shippedBefore")])
async def test_list_kg_units_filters_by_shipment_date(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
    bounds: tuple[str, ...],
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    await create_shipment(batch, batch.first_dev_eui, completed=True)
    await create_shipment(batch, batch.last_dev_eui)
    now = datetime.now(UTC)
    dates = {
        "shippedAfter": (now - timedelta(hours=1)).isoformat(),
        "shippedBefore": (now + timedelta(hours=1)).isoformat(),
    }

    response = await client.get(
        "/api/kg/units",
        params={"batchIdIn": str(batch.id), **{bound: dates[bound] for bound in bounds}},
    )

    assert response.status_code == 200
    assert [item["devEui"] for item in response.json()["items"]] == [batch.first_dev_eui]
    assert response.json()["total"] == 1


@pytest.mark.parametrize("bound", ["shippedAfter", "shippedBefore"])
async def test_list_kg_units_shipment_date_bounds_are_exclusive(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
    bound: str,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)
    assert shipment.completed_at is not None

    response = await client.get(
        "/api/kg/units",
        params={"batchIdIn": str(batch.id), bound: shipment.completed_at.isoformat()},
    )

    assert response.status_code == 200
    assert (response.json()["items"], response.json()["total"]) == ([], 0)


async def test_list_kg_units_shipment_date_filter_excludes_voided_shipments(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
    batch_shipment_service: BatchShipmentService,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)

    async with unit_of_work(session):
        await batch_shipment_service.void_shipment(batch.id, shipment.id, "Cancelled", voided_by_id=None)

    hour_ago = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    response = await client.get("/api/kg/units", params={"batchIdIn": str(batch.id), "shippedAfter": hour_ago})

    assert response.status_code == 200
    assert (response.json()["items"], response.json()["total"]) == ([], 0)


async def test_get_kg_unit_credentials_derives_keys_from_dev_eui(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()
    expected = generate_credentials(batch.first_dev_eui, ActivationType.OTAA, LoRaWanVersion.V1_0)

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui}/credentials")

    assert response.json() == {
        "scheme": "otaa-1.0",
        "devEui": batch.first_dev_eui,
        "joinEui": batch.join_eui,
        "appKey": expected.app_key,
    }


@pytest.mark.parametrize(
    ("activation_type", "lorawan_version", "scheme", "fields"),
    [
        (ActivationType.OTAA, LoRaWanVersion.V1_1, "otaa-1.1", {"joinEui", "appKey", "nwkKey"}),
        (ActivationType.ABP, LoRaWanVersion.V1_0, "abp-1.0", {"devAddr", "nwkSKey", "appSKey"}),
        (
            ActivationType.ABP,
            LoRaWanVersion.V1_1,
            "abp-1.1",
            {"devAddr", "fNwkSIntKey", "sNwkSIntKey", "nwkSEncKey", "appSKey"},
        ),
    ],
)
async def test_get_kg_unit_credentials_has_only_the_fields_of_batch_activation(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
    scheme: str,
    fields: set[str],
) -> None:
    batch = await create_batch()
    async with unit_of_work(session):
        await session.execute(
            update(m.Batch)
            .where(m.Batch.id == batch.id)
            .values(activation_type=activation_type, lorawan_version=lorawan_version)
        )

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui}/credentials")

    assert (response.json()["scheme"], set(response.json())) == (scheme, {"scheme", "devEui", *fields})


async def test_get_kg_unit_credentials_is_not_cached(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/api/kg/units/{batch.first_dev_eui}/credentials")

    assert response.headers["cache-control"] == "no-store"
