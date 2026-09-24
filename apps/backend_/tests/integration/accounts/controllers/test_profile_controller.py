"""Current-user profile routes over HTTP."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.db.enums import UserRole

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import SignIn

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_get_profile_returns_signed_in_user(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
) -> None:
    user = await sign_in(UserRole.OPERATOR)

    response = await client.get("/auth/me")

    assert (response.status_code, response.json()["id"]) == (200, str(user.id))


async def test_update_profile_renames_signed_in_user(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
) -> None:
    await sign_in(UserRole.OPERATOR)

    response = await client.patch("/auth/me", json={"name": "Renamed Actor"})

    assert (response.status_code, response.json()["name"]) == (200, "Renamed Actor")
