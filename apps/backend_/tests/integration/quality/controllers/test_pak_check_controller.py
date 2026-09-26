"""PAK check catalog routes over HTTP with a signed-in engineer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from app.db.enums import UserRole
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import models as m
    from app.domain.quality.services import PakCheckService
    from tests.integration.conftest import SignIn
    from tests.integration.quality.conftest import CreatePak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _engineer(sign_in: SignIn) -> None:
    await sign_in(UserRole.ENGINEER)


@pytest.fixture
async def misconfigured_check(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
) -> m.PakCheck:
    pak = await create_pak()

    async with unit_of_work(session):
        observation = await pak_check_service.observe(
            pak=pak,
            name="rf_power",
            label="RF power",
            defect_group_code="RF",
            seen_at=datetime.now(UTC),
        )

    return observation.check


async def test_list_pak_checks_filters_misconfigured(
    client: AsyncTestClient[Litestar],
    misconfigured_check: m.PakCheck,
) -> None:
    response = await client.get("/verification/checks", params={"misconfigured": "true"})

    assert [item["id"] for item in response.json()["items"]] == [str(misconfigured_check.id)]


async def test_get_pak_check_returns_it(
    client: AsyncTestClient[Litestar],
    misconfigured_check: m.PakCheck,
) -> None:
    response = await client.get(f"/verification/checks/{misconfigured_check.id}")

    assert (response.status_code, response.json()["defectGroupCode"], response.json()["misconfigured"]) == (
        200,
        "RF",
        True,
    )
