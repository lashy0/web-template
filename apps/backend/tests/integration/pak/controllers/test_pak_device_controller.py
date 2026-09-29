"""PAK device routes over HTTP with a signed-in administrator and a real Hydra."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.lib.hydra.exceptions import HydraClientNotFoundError

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from app.lib.hydra import HydraClient
    from tests.integration.conftest import SignIn
    from tests.integration.pak.conftest import CreatePak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _administrator(sign_in: SignIn) -> None:
    await sign_in()


async def test_list_pak_devices_returns_page(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    await create_pak("pak-list")

    response = await client.get("/api/paks")

    assert [item["code"] for item in response.json()["items"]] == ["pak-list"]


async def test_list_pak_devices_filters_by_kind(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    await create_pak("pak-engineering")
    await client.post("/api/paks", json={"code": "pak-otk-line", "kind": "otk_line"})

    response = await client.get("/api/paks", params={"kindIn": "otk_line"})

    assert [item["code"] for item in response.json()["items"]] == ["pak-otk-line"]


async def test_list_pak_devices_filters_by_activity(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    await create_pak("pak-active")
    await client.post("/api/paks", json={"code": "pak-inactive", "kind": "engineering", "isActive": False})

    response = await client.get("/api/paks", params={"active": "false"})

    assert [item["code"] for item in response.json()["items"]] == ["pak-inactive"]


async def test_get_pak_device_returns_it(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-get")

    response = await client.get(f"/api/paks/{pak.id}")

    assert (response.status_code, response.json()["oauthClientId"]) == (200, pak.oauth_client_id)


async def test_create_pak_device_returns_access_key(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/api/paks", json={"code": "pak-create", "kind": "engineering"})

    assert response.status_code == 201
    assert (response.json()["device"]["code"], bool(response.json()["accessKey"])) == ("pak-create", True)


async def test_update_pak_device_changes_code(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-update")

    response = await client.patch(f"/api/paks/{pak.id}", json={"code": "pak-renamed"})

    assert (response.status_code, response.json()["code"]) == (200, "pak-renamed")


async def _pak_audit_actions(client: AsyncTestClient[Litestar]) -> list[tuple[str, object]]:
    response = await client.get("/api/audit", params={"targetTypeIn": "pak"})
    return [(item["action"], item["details"]) for item in response.json()["items"]]


async def test_update_pak_device_audits_old_and_new_values(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-audit")

    await client.patch(f"/api/paks/{pak.id}", json={"code": "pak-audited", "kind": "engineering"})

    assert ("pak.updated", {"changes": {"code": {"from": "pak-audit", "to": "pak-audited"}}}) in (
        await _pak_audit_actions(client)
    )


async def test_update_pak_device_without_changes_writes_no_audit_entry(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-same")

    await client.patch(f"/api/paks/{pak.id}", json={"code": "pak-same"})

    assert "pak.updated" not in [action for action, _ in await _pak_audit_actions(client)]


async def test_deactivate_pak_device_clears_active_flag(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-deactivate")

    response = await client.post(f"/api/paks/{pak.id}/deactivate")

    assert (response.status_code, response.json()["isActive"]) == (200, False)


async def test_activate_pak_device_sets_active_flag(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-activate")
    await client.post(f"/api/paks/{pak.id}/deactivate")

    response = await client.post(f"/api/paks/{pak.id}/activate")

    assert (response.status_code, response.json()["isActive"]) == (200, True)


async def test_archive_pak_device_sets_archive_time(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-archive")

    response = await client.post(f"/api/paks/{pak.id}/archive")

    assert (response.status_code, response.json()["archivedAt"] is not None) == (200, True)


async def test_restore_pak_device_clears_archive_time(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-restore")
    await client.post(f"/api/paks/{pak.id}/archive")

    response = await client.post(f"/api/paks/{pak.id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_get_pak_access_key_returns_current_key(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, key = await create_pak("pak-key")

    response = await client.get(f"/api/paks/{pak.id}/access-key")

    assert (response.status_code, response.json()["accessKey"]) == (200, key)


async def test_rotate_pak_access_key_returns_new_key(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
) -> None:
    pak, key = await create_pak("pak-rotate")

    response = await client.post(f"/api/paks/{pak.id}/access-key/rotate")

    assert response.status_code == 200
    assert response.json()["accessKey"] not in {"", key}


async def test_delete_pak_device_removes_hydra_client(
    client: AsyncTestClient[Litestar],
    hydra_client: HydraClient,
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-delete")

    response = await client.delete(f"/api/paks/{pak.id}")

    assert response.status_code == 204

    with pytest.raises(HydraClientNotFoundError):
        await hydra_client.get_client(pak.oauth_client_id)
