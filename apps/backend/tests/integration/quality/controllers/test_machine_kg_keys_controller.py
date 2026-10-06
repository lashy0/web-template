"""PAK machine API route for KG unit keys over HTTP with a real Hydra access token."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import MulticastGroups
    from tests.integration.quality.conftest import CreateBatch, SignInPak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_get_machine_kg_keys_returns_keys_and_multicast_groups(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
    multicast_groups: MulticastGroups,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()

    response = await client.get(f"/api/machine/kg/units/{batch.first_dev_eui.upper()}/keys", headers=headers)

    body = response.json()
    assert (
        response.status_code,
        body["devEui"],
        body["keys"]["scheme"],
        body["keys"]["joinEui"],
        [group["mcAddr"] for group in body["multicast"]],
    ) == (
        200,
        batch.first_dev_eui,
        "otaa-1.0",
        batch.join_eui,
        [multicast_groups[0].mc_addr, multicast_groups[1].mc_addr],
    )


async def test_get_machine_kg_keys_is_not_cached(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
) -> None:
    batch = await create_batch()
    _, headers = await sign_in_pak()

    response = await client.get(f"/api/machine/kg/units/{batch.first_dev_eui}/keys", headers=headers)

    assert response.headers["cache-control"] == "no-store"


async def test_get_machine_kg_keys_of_unknown_kg_returns_error_code(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
    sign_in_pak: SignInPak,
) -> None:
    await create_batch()
    _, headers = await sign_in_pak()

    response = await client.get("/api/machine/kg/units/ffffffffffffffff/keys", headers=headers)

    assert (response.status_code, response.json()["extra"]["code"]) == (404, "verification_kg_not_found")


async def test_get_machine_kg_keys_without_token_is_unauthorized(
    client: AsyncTestClient[Litestar],
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    response = await client.get(f"/api/machine/kg/units/{batch.first_dev_eui}/keys")

    assert response.status_code == 401
