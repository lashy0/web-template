"""PAK machine API route that returns the calling PAK."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from tests.integration.pak.conftest import CreatePak, IssueAccessToken

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_get_machine_pak_returns_the_calling_pak(
    client: AsyncTestClient[Litestar],
    create_pak: CreatePak,
    issue_access_token: IssueAccessToken,
) -> None:
    pak, key = await create_pak("pak-machine-self")
    token = await issue_access_token(pak.oauth_client_id, key)

    response = await client.get("/api/machine/pak", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"code": "pak-machine-self", "kind": "engineering"}
