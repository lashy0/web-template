"""Packing routes over HTTP with a signed-in packer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select, update

from app.db import models as m
from app.db.enums import KgOtkStatus, UserRole
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


@pytest.fixture(name="packer", autouse=True)
async def fx_packer(sign_in: SignIn) -> m.User:
    return await sign_in(UserRole.PACKER)


async def _pass_otk(session: AsyncSession, dev_eui: str) -> None:
    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit)
            .where(m.KgUnit.dev_eui == dev_eui)
            .values(otk_status=KgOtkStatus.PASSED)
        )


async def test_find_unit_by_short_id_returns_label_data(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5", "ab1")
    batch = await create_batch(prefix)
    await _pass_otk(session, batch.first_dev_eui)

    response = await client.get("/packing/units/AB1-000001")

    body = response.json()
    assert (response.status_code, body["devEui"], body["batch"]["joinEui"], body["canPack"], body["blockedBy"]) == (
        200,
        batch.first_dev_eui,
        batch.join_eui,
        True,
        None,
    )


async def test_find_unit_not_verified_names_blocker(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/packing/units/{batch.first_dev_eui}")

    assert (response.json()["canPack"], response.json()["blockedBy"]) == (False, "packing_otk_not_passed")


async def test_find_unknown_unit_is_not_found(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/packing/units/ab1-ffffff")

    assert response.status_code == 404


async def test_pack_unit_returns_packed_unit(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()
    await _pass_otk(session, batch.first_dev_eui)

    response = await client.post(f"/packing/units/{batch.first_dev_eui.upper()}/pack")

    body = response.json()
    assert (response.status_code, body["state"], body["packedAt"] is not None, body["blockedBy"]) == (
        200,
        "packed",
        True,
        "packing_kg_already_packed",
    )


async def test_pack_unit_writes_audit_entry(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _pass_otk(session, batch.first_dev_eui)

    await client.post(f"/packing/units/{batch.first_dev_eui}/pack")

    entry = await session.scalar(
        select(m.AuditLog)
        .where(m.AuditLog.target_id == batch.first_dev_eui)
    )
    assert entry is not None
    assert (entry.action, entry.actor_id) == ("kg.packed", packer.id)


async def test_pack_packed_unit_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()
    await _pass_otk(session, batch.first_dev_eui)
    await client.post(f"/packing/units/{batch.first_dev_eui}/pack")

    response = await client.post(f"/packing/units/{batch.first_dev_eui}/pack")

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "packing_kg_already_packed"})


async def test_packed_unit_shows_packer_in_kg_units(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    sign_in: SignIn,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _pass_otk(session, batch.first_dev_eui)
    await client.post(f"/packing/units/{batch.first_dev_eui}/pack")
    await sign_in(UserRole.ADMINISTRATOR)

    response = await client.get(f"/kg/units/{batch.first_dev_eui}")

    assert response.json()["packedBy"] == {"id": str(packer.id), "name": packer.name}
