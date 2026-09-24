"""Read-only KG unit routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import update

from app.db import models as m
from app.db.enums import KgState
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import CreateBatch, CreatePrefix

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

    response = await client.get("/kg/units", params={"batchIdIn": str(batch.id)})

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

    response = await client.get("/kg/units", params={"stateIn": "scrapped"})

    assert [item["devEui"] for item in response.json()["items"]] == [batch.last_dev_eui]


async def test_list_kg_units_finds_short_id(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5", "ab1")
    await create_batch(prefix, planned_qty=3)

    response = await client.get("/kg/units", params={"searchString": "AB1-000002"})

    assert [item["shortId"] for item in response.json()["items"]] == ["ab1-000002"]


async def test_get_kg_unit_accepts_upper_case_dev_eui(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/kg/units/{batch.first_dev_eui.upper()}")

    assert (response.status_code, response.json()["batch"]) == (200, {"id": str(batch.id), "name": batch.name})


async def test_get_kg_unit_with_malformed_dev_eui_is_bad_request(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/kg/units/not-a-dev-eui")

    assert response.status_code == 400


async def test_get_missing_kg_unit_is_not_found(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/kg/units/ffffffffffffffff")

    assert response.status_code == 404


async def test_get_kg_unit_shows_batch_lorawan_settings(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/kg/units/{batch.first_dev_eui}")

    assert (response.json()["activationType"], response.json()["lorawanVersion"]) == ("otaa", "1.0")
