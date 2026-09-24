"""The production policy applies to signed-in users."""

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
    pytest.mark.auth,
    pytest.mark.security,
]


async def test_user_without_permission_is_forbidden(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
) -> None:
    await sign_in(UserRole.OPERATOR)

    response = await client.get("/production-orders")

    assert response.status_code == 403
