"""Browser sessions resolve to an active local user."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import Settings
    from tests.integration.conftest import SignIn

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.auth,
]


async def test_unknown_session_is_unauthorized(client: AsyncTestClient[Litestar], settings: Settings) -> None:
    client.cookies.set(settings.kratos.session_cookie, "unknown-session")

    response = await client.get("/auth/me")

    assert response.status_code == 401


async def test_session_of_archived_user_is_unauthorized(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    sign_in: SignIn,
) -> None:
    user = await sign_in()

    async with unit_of_work(session):
        user.archived_at = datetime.now(UTC)
        session.add(user)

    response = await client.get("/auth/me")

    assert response.status_code == 401
