"""Multicast group routes over HTTP with a signed-in administrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.db.enums import UserRole

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import MulticastGroups, OpenEventStream, SignIn

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]

GROUPS = "/api/kg/multicast-groups"


async def test_list_multicast_groups_filters_by_group_id(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in()

    response = await client.get(GROUPS, params={"groupIdIn": "1"})

    assert [item["id"] for item in response.json()["items"]] == [str(multicast_groups[1].id)]


async def test_list_multicast_groups_is_open_to_managers(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in(UserRole.MANAGER)

    response = await client.get(GROUPS)

    assert (response.status_code, response.json()["total"]) == (200, len(multicast_groups))


async def test_get_multicast_group_returns_it_without_keys(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in()
    group = multicast_groups[0]

    response = await client.get(f"{GROUPS}/{group.id}")

    assert response.json() == {
        "id": str(group.id),
        "name": group.name,
        "groupId": 0,
        "mcAddr": group.mc_addr,
        "frequencyHz": 869_100_000,
        "datarate": 0,
        "archivedAt": None,
        "createdAt": response.json()["createdAt"],
        "updatedAt": response.json()["updatedAt"],
    }


async def test_create_multicast_group_generates_address(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
) -> None:
    await sign_in()

    response = await client.post(GROUPS, json={"name": "Updates", "groupId": 0})

    assert (response.status_code, len(response.json()["mcAddr"]), response.json()["frequencyHz"]) == (
        201,
        8,
        869_100_000,
    )


async def test_get_multicast_group_keys_is_not_cached(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in()
    group = multicast_groups[0]

    response = await client.get(f"{GROUPS}/{group.id}/keys")

    assert (response.json()["mcKey"], response.headers["cache-control"]) == (group.mc_key, "no-store")


async def test_get_multicast_group_keys_is_forbidden_to_managers(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in(UserRole.MANAGER)

    response = await client.get(f"{GROUPS}/{multicast_groups[0].id}/keys")

    assert response.status_code == 403


async def test_update_multicast_group_changes_given_fields(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in()
    group = multicast_groups[0]

    response = await client.patch(
        f"{GROUPS}/{group.id}",
        json={"expectedUpdatedAt": group.updated_at.isoformat(), "name": "Updates", "datarate": 2},
    )

    assert (response.status_code, response.json()["name"], response.json()["datarate"]) == (200, "Updates", 2)


async def test_archive_multicast_group_sets_archive_time(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in()

    response = await client.post(f"{GROUPS}/{multicast_groups[0].id}/archive")

    assert (response.status_code, response.json()["archivedAt"] is not None) == (200, True)


async def test_restore_multicast_group_clears_archive_time(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in()
    await client.post(f"{GROUPS}/{multicast_groups[0].id}/archive")

    response = await client.post(f"{GROUPS}/{multicast_groups[0].id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_delete_unused_multicast_group_removes_it(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
) -> None:
    await sign_in()
    group = multicast_groups[0]

    response = await client.delete(f"{GROUPS}/{group.id}")

    assert response.status_code == 204
    assert (await client.get(f"{GROUPS}/{group.id}")).status_code == 404


async def test_archive_multicast_group_announces_the_change(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    multicast_groups: MulticastGroups,
    open_event_stream: OpenEventStream,
) -> None:
    await sign_in()
    group = multicast_groups[0]

    async with open_event_stream() as events:
        await client.post(f"{GROUPS}/{group.id}/archive")
        event = await events.next_event()

    assert event == ("multicast_group.changed", {"multicastGroupId": str(group.id)})
