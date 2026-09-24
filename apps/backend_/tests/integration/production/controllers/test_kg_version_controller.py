"""KG version routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import SignIn
    from tests.integration.production.conftest import CreateVersion

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _administrator(sign_in: SignIn) -> None:
    await sign_in()


async def test_list_kg_versions_returns_page(
    client: AsyncTestClient[Litestar],
    create_version: CreateVersion,
) -> None:
    await create_version("v1")

    response = await client.get("/kg/versions")

    assert [item["code"] for item in response.json()["items"]] == ["v1"]


async def test_get_kg_version_returns_it(
    client: AsyncTestClient[Litestar],
    create_version: CreateVersion,
) -> None:
    version = await create_version("v1")

    response = await client.get(f"/kg/versions/{version.id}")

    assert (response.status_code, response.json()["code"]) == (200, "v1")


async def test_create_kg_version_returns_created_version(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/kg/versions", json={"code": "v1", "name": "Rev. A"})

    assert (response.status_code, response.json()["name"]) == (201, "Rev. A")


async def test_update_kg_version_changes_given_fields(
    client: AsyncTestClient[Litestar],
    create_version: CreateVersion,
) -> None:
    version = await create_version("v1")

    response = await client.patch(f"/kg/versions/{version.id}", json={"description": "Rev. B board"})

    assert (response.status_code, response.json()["description"]) == (200, "Rev. B board")


async def test_archive_kg_version_sets_archive_time(
    client: AsyncTestClient[Litestar],
    create_version: CreateVersion,
) -> None:
    version = await create_version()

    response = await client.post(f"/kg/versions/{version.id}/archive")

    assert (response.status_code, response.json()["archivedAt"] is not None) == (200, True)


async def test_restore_kg_version_clears_archive_time(
    client: AsyncTestClient[Litestar],
    create_version: CreateVersion,
) -> None:
    version = await create_version(archived=True)

    response = await client.post(f"/kg/versions/{version.id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_delete_kg_version_removes_it(
    client: AsyncTestClient[Litestar],
    create_version: CreateVersion,
) -> None:
    version = await create_version()

    response = await client.delete(f"/kg/versions/{version.id}")

    assert response.status_code == 204
    assert (await client.get(f"/kg/versions/{version.id}")).status_code == 404
