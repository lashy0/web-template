"""User management routes over HTTP with a signed-in administrator and a real Kratos."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from app.db.enums import UserRole
from app.lib.kratos.exceptions import KratosIdentityNotFoundError

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from app.lib.kratos import KratosClient
    from tests.integration.accounts.conftest import CreateUser
    from tests.integration.conftest import SignIn

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
async def _administrator(sign_in: SignIn) -> None:
    await sign_in()


async def test_list_users_returns_page(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.get("/users", params={"searchString": user.identity_login})

    assert [item["id"] for item in response.json()["items"]] == [str(user.id)]


async def test_get_user_returns_it(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.get(f"/users/{user.id}")

    assert (response.status_code, response.json()["login"]) == (200, user.identity_login)


async def test_create_user_returns_created_user(
    client: AsyncTestClient[Litestar],
    kratos_client: KratosClient,
) -> None:
    # Kratos identities outlive per-test database cleanup, so logins must be unique.
    # Hyphens break runs of four equal characters, which a login may not contain;
    # the fixed digit keeps the password valid when the suffix has none.
    suffix = uuid4().hex[:9]
    login = f"user-{suffix[:3]}-{suffix[3:6]}-{suffix[6:]}"

    response = await client.post(
        "/users",
        json={"login": login, "name": "Test User", "password": f"Test_User_{suffix}_1!", "role": "operator"},
    )

    assert response.status_code == 201
    assert (await kratos_client.get_identity(response.json()["identityId"])).login == login


async def test_update_user_renames_it(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.patch(f"/users/{user.id}", json={"name": "Renamed User"})

    assert (response.status_code, response.json()["name"]) == (200, "Renamed User")


async def test_update_user_role_assigns_role(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.put(f"/users/{user.id}/role", json={"role": UserRole.MANAGER.value})

    assert (response.status_code, response.json()["role"]) == (200, "manager")


async def test_update_user_password_answers_no_content(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.put(f"/users/{user.id}/password", json={"password": "Another_Password_2026!"})

    assert response.status_code == 204


async def test_deactivate_user_clears_active_flag(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.post(f"/users/{user.id}/deactivate")

    assert (response.status_code, response.json()["isActive"]) == (200, False)


async def test_activate_user_sets_active_flag(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user(is_active=False)

    response = await client.post(f"/users/{user.id}/activate")

    assert (response.status_code, response.json()["isActive"]) == (200, True)


async def test_archive_user_sets_archive_time(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.post(f"/users/{user.id}/archive")

    assert (response.status_code, response.json()["archivedAt"] is not None) == (200, True)


async def test_restore_user_clears_archive_time(
    client: AsyncTestClient[Litestar],
    create_user: CreateUser,
) -> None:
    user = await create_user()
    await client.post(f"/users/{user.id}/archive")

    response = await client.post(f"/users/{user.id}/restore")

    assert (response.status_code, response.json()["archivedAt"]) == (200, None)


async def test_delete_user_removes_kratos_identity(
    client: AsyncTestClient[Litestar],
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    user = await create_user()

    response = await client.delete(f"/users/{user.id}")

    assert response.status_code == 204

    with pytest.raises(KratosIdentityNotFoundError):
        await kratos_client.get_identity(user.identity_id)
