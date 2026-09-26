"""Defect group routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.db import models as m

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import SignIn
    from tests.integration.quality.conftest import CreateGroup, CreateType

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _administrator(sign_in: SignIn) -> None:
    await sign_in()


async def test_list_defect_groups_returns_page_with_counts(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group("RF")
    await create_type(group, "RF_LOW")
    await create_type(group, "RF_NONE", archived=True)

    response = await client.get("/defects/groups")

    assert response.status_code == 200
    assert [(item["code"], item["typesCount"], item["activeTypesCount"]) for item in response.json()["items"]] == [
        ("RF", 2, 1)
    ]


async def test_list_defect_groups_searches_code_ignoring_case(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
) -> None:
    await create_group("RF")
    await create_group("PWR")

    response = await client.get("/defects/groups", params={"searchString": "rf"})

    assert [item["code"] for item in response.json()["items"]] == ["RF"]


async def test_list_defect_groups_filters_archived(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
) -> None:
    await create_group("RF")
    await create_group("PWR", archived=True)

    response = await client.get("/defects/groups", params={"archived": "true"})

    assert [item["code"] for item in response.json()["items"]] == ["PWR"]


async def test_get_defect_group_returns_it(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
) -> None:
    group = await create_group("RF")

    response = await client.get(f"/defects/groups/{group.id}")

    assert (response.status_code, response.json()["code"]) == (200, "RF")


async def test_create_defect_group_returns_it(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/defects/groups", json={"code": "RF", "name": "Radio", "description": "RF faults"})

    assert response.status_code == 201
    assert (response.json()["code"], response.json()["typesCount"]) == ("RF", 0)


async def test_create_defect_group_with_taken_code_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
) -> None:
    await create_group("RF")

    response = await client.post("/defects/groups", json={"code": "RF", "name": "Radio"})

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "defect_group_code_taken"})


async def test_create_defect_group_with_spaced_code_is_bad_request(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/defects/groups", json={"code": "RF LOW", "name": "Radio"})

    assert response.status_code == 400


async def test_create_defect_group_writes_audit_entry(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
) -> None:
    response = await client.post("/defects/groups", json={"code": "RF", "name": "Radio"})

    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.target_id == response.json()["id"]))
    assert entry is not None
    assert entry.action == "defect_group.created"


async def test_update_defect_group_changes_given_fields(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
) -> None:
    group = await create_group("RF")

    response = await client.patch(f"/defects/groups/{group.id}", json={"name": "Radio"})

    assert (response.status_code, response.json()["name"]) == (200, "Radio")


async def test_archive_defect_group_with_active_type_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group("RF")
    await create_type(group)

    response = await client.post(f"/defects/groups/{group.id}/archive")

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "defect_group_has_active_types"})


async def test_restore_defect_group_restores_it(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
) -> None:
    group = await create_group("RF", archived=True)

    response = await client.post(f"/defects/groups/{group.id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_delete_defect_group_with_type_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    group = await create_group("RF")
    await create_type(group)

    response = await client.delete(f"/defects/groups/{group.id}")

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "defect_group_in_use"})


async def test_delete_defect_group_removes_it(
    client: AsyncTestClient[Litestar],
    create_group: CreateGroup,
) -> None:
    group = await create_group("RF")

    response = await client.delete(f"/defects/groups/{group.id}")

    assert (response.status_code, (await client.get(f"/defects/groups/{group.id}")).status_code) == (204, 404)
