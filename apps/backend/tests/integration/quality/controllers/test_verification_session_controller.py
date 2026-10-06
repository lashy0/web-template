"""Verification session routes over HTTP with a signed-in engineer."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from app.db import models as m
from app.db.enums import UserRole
from app.domain.quality.schemas import (
    VerificationSessionOpen,
    VerificationStepComplete,
    VerificationStepResult,
    VerificationStepStart,
)
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

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
        item, _ = await verification_service.open_session(
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
    response = await client.get("/api/verification/sessions", params={"batchIdIn": str(verification_session.batch_id)})

    assert [item["id"] for item in response.json()["items"]] == [str(verification_session.id)]


async def test_list_verification_sessions_filters_by_dev_eui(
    client: AsyncTestClient[Litestar],
    verification_session: m.VerificationSession,
) -> None:
    response = await client.get("/api/verification/sessions", params={"devEuiIn": verification_session.dev_eui})

    assert [item["id"] for item in response.json()["items"]] == [str(verification_session.id)]


async def test_get_verification_session_returns_its_steps(
    client: AsyncTestClient[Litestar],
    verification_session: m.VerificationSession,
) -> None:
    response = await client.get(f"/api/verification/sessions/{verification_session.id}")

    assert response.status_code == 200
    assert [step["checkName"] for step in response.json()["steps"]] == ["rf_power"]


async def test_get_verification_session_shows_the_kg_version_of_the_batch(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    verification_session: m.VerificationSession,
) -> None:
    async with unit_of_work(session):
        version = m.KgVersion(code=f"kg-{uuid4().hex[:6]}", name="Слон версии 3")
        session.add(version)
        await session.flush()
        batch = await session.get_one(m.Batch, verification_session.batch_id)
        batch.kg_version_id = version.id

    response = await client.get(f"/api/verification/sessions/{verification_session.id}")

    assert (response.json()["firmwareVersion"], response.json()["kgVersion"]) == (
        "1.0.0",
        {"id": str(version.id), "code": version.code, "name": "Слон версии 3"},
    )


async def test_verification_session_of_a_batch_without_kg_version_has_none(
    client: AsyncTestClient[Litestar],
    verification_session: m.VerificationSession,
) -> None:
    response = await client.get(f"/api/verification/sessions/{verification_session.id}")

    assert response.json()["kgVersion"] is None


async def test_list_verification_sessions_counts_completed_steps(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    verification_service: VerificationSessionService,
    verification_session: m.VerificationSession,
) -> None:
    before = await client.get("/api/verification/sessions")

    async with unit_of_work(session):
        await verification_service.complete_step(
            verification_session.pak,
            verification_session.id,
            1,
            VerificationStepComplete(status=VerificationStepResult.PASSED),
        )
    after = await client.get("/api/verification/sessions")

    assert [item["completedSteps"] for item in (*before.json()["items"], *after.json()["items"])] == [0, 1]


async def test_list_verification_sessions_by_slot_returns_the_slots_of_the_pak(
    client: AsyncTestClient[Litestar],
    verification_session: m.VerificationSession,
) -> None:
    response = await client.get(
        "/api/verification/sessions/by-slot",
        params={"pakId": str(verification_session.pak_id)},
    )

    assert response.status_code == 200
    assert [(item["slotNo"], item["id"]) for item in response.json()] == [(1, str(verification_session.id))]


async def test_list_verification_sessions_by_slot_returns_the_steps_started_so_far(
    client: AsyncTestClient[Litestar],
    verification_session: m.VerificationSession,
) -> None:
    response = await client.get(
        "/api/verification/sessions/by-slot",
        params={"pakId": str(verification_session.pak_id)},
    )

    assert response.json()[0]["steps"] == [{"stepNo": 1, "checkLabel": "RF power", "status": "running"}]
