"""PAK machine API routes over HTTP with a real Hydra access token."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import select

from app.db import models as m
from app.db.enums import KgOtkStatus, UserRole

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import OpenEventStream, SignIn
    from tests.integration.quality.conftest import CreateBatch, SignInPak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]

SESSIONS = "/api/machine/verification/sessions"


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
        headers={**headers, "User-Agent": "PAK firmware/1.0"},
    )

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.action == "pak_check.created"))
    assert response.status_code == 201
    assert entry is not None
    assert (entry.target_label, entry.actor_id, entry.actor_login, entry.actor_name, entry.details) == (
        "RF power",
        None,
        pak.code,
        None,
        {"pak_id": str(pak.id), "name": "rf_power", "defect_group_code": "RF"},
    )
    assert entry.user_agent == "PAK firmware/1.0"
    assert entry.ip_address is not None


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


async def test_open_verification_session_announces_the_change_to_users_who_read_verification(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    pak, headers = await sign_in_pak()
    await sign_in(UserRole.ENGINEER)

    async with open_event_stream() as events:
        await _open(client, headers, batch.first_dev_eui)
        event = await events.next_event()

    assert event == ("verification.changed", {"pakId": str(pak.id), "batchId": str(batch.id)})


async def test_start_verification_step_announces_a_new_check(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    pak, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui)
    await sign_in(UserRole.ENGINEER)

    async with open_event_stream() as events:
        await _start(client, headers, opened["id"])
        received = [await events.next_event(), await events.next_event()]

    check_id = await session.scalar(select(m.PakCheck.id).where(m.PakCheck.name == "rf_power"))
    assert ("pak_check.changed", {"checkId": str(check_id)}) in received
    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.action == "pak_check.created"))
    assert entry is not None
    assert (entry.actor_id, entry.actor_login, entry.actor_name) == (None, pak.code, None)


async def test_repeated_step_start_does_not_audit_or_announce_the_check_again(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    pak, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui)
    await _start(client, headers, opened["id"])
    await sign_in(UserRole.ENGINEER)

    async with open_event_stream() as events:
        await _start(client, headers, opened["id"])
        event = await events.next_event()

        with pytest.raises(TimeoutError):
            await events.next_event(timeout=0.3)

    entries = list(await session.scalars(select(m.AuditLog).where(m.AuditLog.target_type == "pak_check")))
    assert len(entries) == 1
    assert event == ("verification.changed", {"pakId": str(pak.id), "batchId": str(batch.id)})


async def test_unchanged_check_in_a_new_step_does_not_audit_or_announce_the_check(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    pak, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui, total_steps=2)
    await _start(client, headers, opened["id"])
    completed = await client.put(f"{SESSIONS}/{opened['id']}/steps/1", json={"status": "passed"}, headers=headers)
    completed.raise_for_status()
    await sign_in(UserRole.ENGINEER)

    async with open_event_stream() as events:
        response = await client.post(
            f"{SESSIONS}/{opened['id']}/steps",
            json={"stepNo": 2, "checkName": "rf_power", "checkLabel": "RF power", "defectGroupCode": "RF"},
            headers=headers,
        )
        event = await events.next_event()

        with pytest.raises(TimeoutError):
            await events.next_event(timeout=0.3)

    entries = list(await session.scalars(select(m.AuditLog).where(m.AuditLog.target_type == "pak_check")))
    assert response.status_code == 201
    assert len(entries) == 1
    assert event == ("verification.changed", {"pakId": str(pak.id), "batchId": str(batch.id)})


async def test_updated_check_is_audited_and_announced_by_the_pak(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    pak, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui, total_steps=2)
    await _start(client, headers, opened["id"])
    completed = await client.put(f"{SESSIONS}/{opened['id']}/steps/1", json={"status": "passed"}, headers=headers)
    completed.raise_for_status()
    await sign_in(UserRole.ENGINEER)

    async with open_event_stream() as events:
        response = await client.post(
            f"{SESSIONS}/{opened['id']}/steps",
            json={"stepNo": 2, "checkName": "rf_power", "checkLabel": "RF power", "defectGroupCode": "POWER"},
            headers=headers,
        )
        received = [await events.next_event(), await events.next_event()]

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.action == "pak_check.updated"))
    assert response.status_code == 201
    assert entry is not None
    assert (entry.actor_id, entry.actor_login, entry.actor_name) == (None, pak.code, None)
    assert entry.details == {
        "pak_id": str(pak.id),
        "name": "rf_power",
        "changes": {"defect_group_code": {"from": "RF", "to": "POWER"}},
    }
    assert ("pak_check.changed", {"checkId": entry.target_id}) in received


async def test_replacing_a_session_announces_once_for_the_same_pak_and_batch(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    pak, headers = await sign_in_pak()
    await _open(client, headers, batch.first_dev_eui)
    await sign_in(UserRole.ENGINEER)

    async with open_event_stream() as events:
        await _open(client, headers, batch.last_dev_eui)
        event = await events.next_event()

        with pytest.raises(TimeoutError):
            await events.next_event(timeout=0.3)

    assert event == ("verification.changed", {"pakId": str(pak.id), "batchId": str(batch.id)})


async def test_complete_verification_session_on_otk_line_pak_announces_the_batch_change(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()
    opened = await _open(client, headers, batch.first_dev_eui)
    await _start(client, headers, opened["id"])
    await client.put(f"{SESSIONS}/{opened['id']}/steps/1", json={"status": "passed"}, headers=headers)
    await sign_in(UserRole.MANAGER)

    async with open_event_stream() as events:
        await client.post(f"{SESSIONS}/{opened['id']}/complete", json={"status": "passed"}, headers=headers)
        received = [await events.next_event(), await events.next_event()]

    assert ("batch.changed", {"batchId": str(batch.id)}) in received


async def test_open_verification_session_is_not_announced_to_users_who_cannot_read_verification(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in: SignIn,
    sign_in_pak: SignInPak,
    open_event_stream: OpenEventStream,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()
    await sign_in(UserRole.PACKER)

    async with open_event_stream() as events:
        await _open(client, headers, batch.first_dev_eui)

        with pytest.raises(TimeoutError):
            await events.next_event(timeout=0.3)
