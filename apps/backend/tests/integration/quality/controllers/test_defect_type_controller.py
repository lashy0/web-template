"""Defect type routes over HTTP with a signed-in user."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.db.enums import UserRole

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import OpenEventStream, SignIn
    from tests.integration.quality.conftest import CreateGroup, CreateType

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_list_defect_types_filters_by_group(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    await sign_in()
    radio = await create_group("RF")
    await create_type(radio, "RF_LOW")
    await create_type(await create_group("PWR"), "PWR_LOW")

    response = await client.get("/api/defects/types", params={"groupIdIn": str(radio.id)})

    assert response.status_code == 200
    assert [(item["code"], item["group"]["code"]) for item in response.json()["items"]] == [("RF_LOW", "RF")]


async def test_get_defect_type_returns_guidance(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    await sign_in()
    defect_type = await create_type(await create_group())

    response = await client.get(f"/api/defects/types/{defect_type.id}")

    assert (response.status_code, response.json()["description"]) == (200, "Weak signal")


async def test_create_defect_type_returns_it(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
) -> None:
    await sign_in()
    group = await create_group("RF")

    response = await client.post(
        "/api/defects/types",
        json={
            "groupId": str(group.id),
            "code": "RF_LOW",
            "name": "Low signal",
            "description": "RSSI below the limit",
            "engineerAction": "Check the antenna",
        },
    )

    assert response.status_code == 201
    assert (response.json()["group"]["code"], response.json()["engineerAction"]) == ("RF", "Check the antenna")


async def test_create_defect_type_in_archived_group_is_conflict_with_code(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
) -> None:
    await sign_in()
    group = await create_group("RF", archived=True)

    response = await client.post(
        "/api/defects/types",
        json={"groupId": str(group.id), "code": "RF_LOW", "name": "Low", "description": "Weak"},
    )

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "defect_group_archived"})


async def test_update_defect_type_clears_guidance(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    await sign_in()
    defect_type = await create_type(await create_group())
    first = await client.patch(
        f"/api/defects/types/{defect_type.id}",
        json={"expectedUpdatedAt": defect_type.updated_at.isoformat(), "possibleCause": "Loose antenna"},
    )

    response = await client.patch(
        f"/api/defects/types/{defect_type.id}",
        json={"expectedUpdatedAt": first.json()["updatedAt"], "possibleCause": None},
    )

    assert (response.status_code, response.json()["possibleCause"]) == (200, None)


async def test_archive_and_restore_defect_type(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    await sign_in()
    defect_type = await create_type(await create_group())

    archived = await client.post(f"/api/defects/types/{defect_type.id}/archive")
    restored = await client.post(f"/api/defects/types/{defect_type.id}/restore")

    assert (archived.json()["archivedAt"] is not None, restored.json()["archivedAt"]) == (True, None)


async def test_delete_defect_type_removes_it(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
    create_type: CreateType,
) -> None:
    await sign_in()
    defect_type = await create_type(await create_group())

    response = await client.delete(f"/api/defects/types/{defect_type.id}")

    assert (response.status_code, (await client.get(f"/api/defects/types/{defect_type.id}")).status_code) == (204, 404)


async def test_engineer_reads_but_cannot_create_defect_types(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
) -> None:
    await sign_in(UserRole.ENGINEER)
    group = await create_group("RF")

    listed = await client.get("/api/defects/types")
    created = await client.post(
        "/api/defects/types",
        json={"groupId": str(group.id), "code": "RF_LOW", "name": "Low", "description": "Weak"},
    )

    assert (listed.status_code, created.status_code) == (200, 403)


async def test_archive_defect_type_announces_the_type_change(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
    create_group: CreateGroup,
    create_type: CreateType,
    open_event_stream: OpenEventStream,
) -> None:
    await sign_in()
    defect_type = await create_type(await create_group())

    async with open_event_stream() as events:
        await client.post(f"/api/defects/types/{defect_type.id}/archive")
        event = await events.next_event()

    assert event == ("defect_type.changed", {"typeId": str(defect_type.id)})
