"""Verification session routes over HTTP with a signed-in engineer."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from app.db.enums import UserRole
from app.domain.quality.schemas import VerificationSessionOpen, VerificationStepStart
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import models as m
    from app.domain.quality.services import PakCheckService, VerificationSessionService
    from tests.integration.conftest import SignIn
    from tests.integration.quality.conftest import CreateBatch, CreatePak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _engineer(sign_in: SignIn) -> None:
    await sign_in(UserRole.ENGINEER)


@pytest.fixture
async def verification_session(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> m.VerificationSession:
    batch = await create_batch()
    pak = await create_pak()

    async with unit_of_work(session):
        item = await verification_service.open_session(
            pak,
            VerificationSessionOpen(dev_eui=batch.first_dev_eui, slot_no=1, firmware_version="1.0.0", total_steps=1),
            reopen_inactivity=timedelta(minutes=60),
        )
        await verification_service.start_step(
            pak,
            item.id,
            VerificationStepStart(step_no=1, check_name="rf_power", check_label="RF power", defect_group_code="RF"),
            checks=pak_check_service,
        )

    return item


async def test_list_verification_sessions_filters_by_batch(
    client: AsyncTestClient[Litestar],
    verification_session: m.VerificationSession,
) -> None:
    response = await client.get("/verification/sessions", params={"batchIdIn": str(verification_session.batch_id)})

    assert [item["id"] for item in response.json()["items"]] == [str(verification_session.id)]


async def test_get_verification_session_returns_its_steps(
    client: AsyncTestClient[Litestar],
    verification_session: m.VerificationSession,
) -> None:
    response = await client.get(f"/verification/sessions/{verification_session.id}")

    assert response.status_code == 200
    assert [step["checkName"] for step in response.json()["steps"]] == ["rf_power"]
