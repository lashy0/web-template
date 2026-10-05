"""Check server health and OAuth client credentials."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Literal

import httpx2
import msgspec

from pak_simulator.client import PakClient
from pak_simulator.contracts import ClientFactory
from pak_simulator.errors import ApiError, ClientError, InvalidResponseError, error_message
from pak_simulator.model import Pak, Simulation


class _Health(msgspec.Struct):
    database_status: Literal["online", "offline"]
    kratos_status: Literal["online", "offline"]
    hydra_status: Literal["online", "offline"]


@dataclass(frozen=True, slots=True)
class Probe:
    target: str
    status: Literal["OK", "ERROR"]
    detail: str


async def _server_probe(
    simulation: Simulation,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> Probe:
    try:
        async with httpx2.AsyncClient(
            timeout=10,
            verify=simulation.verify_tls,
            transport=transport,
        ) as client:
            response = await client.get(f"{simulation.server}/api/health")

        if response.status_code not in {200, 503}:
            error = ApiError(response.status_code, None, response.reason_phrase, stage="health")

            return Probe("Server", "ERROR", error_message(error))

        try:
            health = msgspec.json.decode(response.content, type=_Health)
        except msgspec.DecodeError as exc:
            raise InvalidResponseError("health", exc) from exc

        services = {
            "database": health.database_status,
            "Kratos": health.kratos_status,
            "Hydra": health.hydra_status,
        }
        offline = [name for name, status in services.items() if status != "online"]

        if response.status_code != 200 or offline:
            detail = f"Offline: {', '.join(offline)}" if offline else "Health endpoint returned HTTP 503"

            return Probe("Server", "ERROR", detail)

        return Probe("Server", "OK", "API, database, Kratos and Hydra are online")
    except (httpx2.TransportError, InvalidResponseError) as exc:
        return Probe("Server", "ERROR", error_message(exc, stage="health"))


async def check_remote(
    simulation: Simulation,
    *,
    on_start: Callable[[str], None] | None = None,
    client_factory: ClientFactory = PakClient,
    health_transport: httpx2.AsyncBaseTransport | None = None,
) -> AsyncGenerator[Probe]:
    """Yield each result as server health and PAK credentials are checked."""
    if on_start is not None:
        on_start("Server health")

    yield await _server_probe(simulation, health_transport)

    for pak in simulation.paks:
        if on_start is not None:
            on_start(f"{pak.code} credentials")

        yield await _credentials_probe(simulation, pak, client_factory)


async def _credentials_probe(
    simulation: Simulation,
    pak: Pak,
    client_factory: ClientFactory,
) -> Probe:
    client = client_factory(
        server=simulation.server,
        client_id=pak.client_id,
        access_key=pak.access_key,
        verify=simulation.verify_tls,
    )
    try:
        await client.authenticate()

        return Probe(f"{pak.code} credentials", "OK", "OAuth client ID and access key accepted")
    except (ApiError, ClientError, httpx2.TransportError) as exc:
        return Probe(f"{pak.code} credentials", "ERROR", error_message(exc, stage="authentication"))
    finally:
        await client.aclose()
