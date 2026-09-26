"""PAK machine API routes over HTTP with a real Hydra access token."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import select

from app.db import models as m
from app.db.enums import KgOtkStatus

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.quality.conftest import CreateBatch, SignInPak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]

SESSIONS = "/machine/verification/sessions"


async def _open(
    client: AsyncTestClient[Litestar],
    headers: dict[str, str],
    dev_eui: str,
    total_steps: int = 1,
) -> dict[str, Any]:
    response = await client.post(
        SESSIONS,
        json={"devEui": dev_eui, "slotNo": 1, "firmwareVersion": "1.0.0", "totalSteps": total_steps},
        headers=headers,
    )
    response.raise_for_status()

    return dict(response.json())


async def _start(client: AsyncTestClient[Litestar], headers: dict[str, str], session_id: str) -> None:
    response = await client.post(
        f"{SESSIONS}/{session_id}/steps",
        json={"stepNo": 1, "checkName": "rf_power", "checkLabel": "RF power", "defectGroupCode": "RF"},
        headers=headers,
    )
    response.raise_for_status()


async def test_open_verification_session_starts_it(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()

    response = await client.post(
        SESSIONS,
        json={"devEui": batch.first_dev_eui.upper(), "slotNo": 1, "firmwareVersion": "1.0.0", "totalSteps": 3},
        headers=headers,
    )

    assert response.status_code == 201
    assert (response.json()["devEui"], response.json()["status"]) == (batch.first_dev_eui, "running")


async def test_open_verification_session_without_token_is_unauthorized(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.post(
        SESSIONS,
        json={"devEui": batch.first_dev_eui, "slotNo": 1, "firmwareVersion": "1.0.0", "totalSteps": 1},
    )

    assert response.status_code == 401


async def test_start_verification_step_records_the_check_in_the_audit_log(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
) -> None:
    batch = await create_batch()
    pak, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui)

    response = await client.post(
        f"{SESSIONS}/{opened['id']}/steps",
        json={"stepNo": 1, "checkName": "rf_power", "checkLabel": "RF power", "defectGroupCode": "RF"},
        headers=headers,
    )

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.action == "pak_check.created"))
    assert response.status_code == 201
    assert entry is not None
    assert (entry.target_label, entry.actor_login, entry.details) == (
        "RF power",
        pak.code,
        {"pak_id": str(pak.id), "name": "rf_power", "defect_group_code": "RF"},
    )


async def test_start_verification_step_beyond_total_steps_returns_error_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui, total_steps=1)

    response = await client.post(
        f"{SESSIONS}/{opened['id']}/steps",
        json={"stepNo": 2, "checkName": "rf_power", "checkLabel": "RF power", "defectGroupCode": "RF"},
        headers=headers,
    )

    assert (response.status_code, response.json()["extra"]["code"]) == (409, "verification_step_out_of_range")


async def test_complete_verification_step_records_the_result(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui)
    await _start(client, headers, opened["id"])

    response = await client.put(
        f"{SESSIONS}/{opened['id']}/steps/1",
        json={"status": "passed", "measurementValue": 1.5, "measurementUnit": "dBm"},
        headers=headers,
    )

    assert response.status_code == 200
    assert (response.json()["status"], response.json()["measurementUnit"]) == ("passed", "dBm")


async def test_complete_verification_session_on_otk_line_pak_passes_the_kg(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui)
    await _start(client, headers, opened["id"])
    await client.put(f"{SESSIONS}/{opened['id']}/steps/1", json={"status": "passed"}, headers=headers)

    response = await client.post(f"{SESSIONS}/{opened['id']}/complete", json={"status": "passed"}, headers=headers)

    otk_status = await session.scalar(select(m.KgUnit.otk_status).where(m.KgUnit.dev_eui == batch.first_dev_eui))
    assert (response.status_code, otk_status) == (200, KgOtkStatus.PASSED)
