"""DevEUI prefix routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import CreatePrefix

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _administrator(sign_in: SignIn) -> None:
    await sign_in()


async def test_list_kg_prefixes_returns_page(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    await create_prefix("a1b2c3d4e5", "ab1")

    response = await client.get("/kg/prefixes")

    assert [item["prefix"] for item in response.json()["items"]] == ["a1b2c3d4e5"]


async def test_get_kg_prefix_returns_it(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    response = await client.get(f"/kg/prefixes/{prefix.id}")

    assert (response.status_code, response.json()["shortCode"]) == (200, prefix.short_code)


async def test_create_kg_prefix_returns_normalized_prefix(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/kg/prefixes", json={"prefix": "A1B2C3D4E5", "shortCode": "AB1"})

    assert (response.status_code, response.json()["prefix"], response.json()["shortCode"]) == (
        201,
        "a1b2c3d4e5",
        "ab1",
    )


async def test_update_kg_prefix_renames_it(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    response = await client.patch(f"/kg/prefixes/{prefix.id}", json={"name": "Line A"})

    assert (response.status_code, response.json()["name"]) == (200, "Line A")


async def test_archive_kg_prefix_sets_archive_time(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    response = await client.post(f"/kg/prefixes/{prefix.id}/archive")

    assert (response.status_code, response.json()["archivedAt"] is not None) == (200, True)


async def test_restore_kg_prefix_clears_archive_time(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix(archived=True)

    response = await client.post(f"/kg/prefixes/{prefix.id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_delete_kg_prefix_removes_it(
    client: AsyncTestClient[Litestar],
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    response = await client.delete(f"/kg/prefixes/{prefix.id}")

    assert response.status_code == 204
    assert (await client.get(f"/kg/prefixes/{prefix.id}")).status_code == 404
