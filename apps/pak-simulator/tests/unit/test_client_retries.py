from __future__ import annotations

import asyncio
import json

import httpx2
import pytest

from pak_simulator.errors import ApiError, ClientError
from tests.unit.support import TEST_TIMEOUT, mock_client, running_task, yield_control

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


@pytest.mark.parametrize("failure", ["gateway", "transport"])
async def test_verification_retries_preserve_payload(failure: str) -> None:
    attempts: list[bytes] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/token"):
            return httpx2.Response(200, json={"access_token": "token"})

        attempts.append(request.content)

        if len(attempts) == 1:
            if failure == "transport":
                raise httpx2.ReadError("Connection lost", request=request)

            return httpx2.Response(503)

        return httpx2.Response(200, json={"id": "session", **json.loads(request.content)})

    async with mock_client(handler) as client:
        await client.open_session(dev_eui="0000000000000001", slot_no=1, firmware_version="1", total_steps=1)

    assert len(attempts) == 2 and attempts[0] == attempts[1]


@pytest.mark.parametrize("retry_delays", [(), (0,)])
async def test_exhausted_gateway_retries_raise_api_error(retry_delays: tuple[float, ...]) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/token"):
            return httpx2.Response(200, json={"access_token": "token"})

        requests.append(request)

        return httpx2.Response(503)

    async with mock_client(handler, retry_delays=retry_delays) as client:
        with pytest.raises(ApiError) as exc:
            await client.open_session(dev_eui="0000000000000001", slot_no=1, firmware_version="1", total_steps=1)

    assert exc.value.status == 503 and exc.value.stage == "verification"
    assert len(requests) == len(retry_delays) + 1


async def test_authentication_transport_failure_preserves_stage() -> None:
    token_requests = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal token_requests
        token_requests += 1
        raise httpx2.ConnectError("Offline", request=request)

    async with mock_client(handler, retry_delays=(0,)) as client:
        with pytest.raises(ClientError) as exc:
            await client.authenticate()

    assert token_requests == 2
    assert exc.value.stage == "authentication"


@pytest.mark.parametrize("failure", ["gateway", "transport"])
async def test_concurrent_authentication_retries_transient_token_failure(failure: str) -> None:
    token_requests = 0

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal token_requests
        assert request.url.path.endswith("/token")
        token_requests += 1

        if token_requests == 1:
            if failure == "transport":
                raise httpx2.ReadError("Connection lost", request=request)

            return httpx2.Response(503, json={"error": "temporarily_unavailable"})

        return httpx2.Response(200, json={"access_token": "token", "expires_in": 3600})

    async with mock_client(handler, retry_delays=(0,)) as client:
        async with asyncio.timeout(TEST_TIMEOUT):
            await asyncio.gather(*(client.authenticate() for _ in range(6)))

    assert token_requests == 2


async def test_exhausted_transient_token_retries_preserve_authentication_stage() -> None:
    token_requests = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal token_requests
        token_requests += 1

        return httpx2.Response(503, json={"error": "temporarily_unavailable"})

    async with mock_client(handler, retry_delays=(0, 0)) as client:
        with pytest.raises(ApiError) as exc:
            await client.authenticate()

    assert token_requests == 3
    assert exc.value.stage == "authentication"
    assert exc.value.code == "temporarily_unavailable"


@pytest.mark.parametrize("status", [400, 503])
async def test_invalid_credentials_are_not_retried(status: int) -> None:
    token_requests = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal token_requests
        token_requests += 1

        return httpx2.Response(status, json={"error": "invalid_client"})

    async with mock_client(handler, retry_delays=(0, 0)) as client:
        with pytest.raises(ApiError) as exc:
            await client.authenticate()

    assert token_requests == 1
    assert exc.value.stage == "authentication"
    assert exc.value.unauthorized


async def test_token_refresh_preserves_remaining_retry_budget() -> None:
    tokens = 0
    requests: list[httpx2.Request] = []
    delays: list[float] = []
    statuses = iter((503, 401, 503, 503))

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal tokens

        if request.url.path.endswith("/token"):
            tokens += 1

            return httpx2.Response(200, json={"access_token": f"t{tokens}"})

        requests.append(request)

        return httpx2.Response(next(statuses, 503))

    async def sleep(delay: float) -> None:
        delays.append(delay)
        await yield_control(delay)

    async with mock_client(handler, retry_delays=(0.25, 0.75), sleep=sleep) as client:
        with pytest.raises(ApiError) as exc:
            await client.open_session(dev_eui="0000000000000001", slot_no=1, firmware_version="1", total_steps=1)

    assert exc.value.status == 503 and exc.value.stage == "verification"
    assert tokens == 2 and len(requests) == 4
    assert delays == [0.25, 0.75]
    assert [request.headers["Authorization"] for request in requests] == [
        "Bearer t1",
        "Bearer t1",
        "Bearer t2",
        "Bearer t2",
    ]
    assert len({request.content for request in requests}) == 1


async def test_cancellation_during_retry_delay_is_preserved() -> None:
    requests = 0
    sleeping = asyncio.Event()

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal requests
        requests += 1

        return httpx2.Response(503)

    async def sleep(delay: float) -> None:
        assert delay == 0.25
        sleeping.set()
        await asyncio.Event().wait()

    async with mock_client(handler, retry_delays=(0.25, 0.75), sleep=sleep) as client:
        async with running_task(client.authenticate()) as task:
            await asyncio.wait_for(sleeping.wait(), TEST_TIMEOUT)
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, TEST_TIMEOUT)

    assert requests == 1


@pytest.mark.parametrize("status", [400, 401, 403])
async def test_permanent_verification_error_is_not_retried(status: int) -> None:
    requests = 0
    tokens = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal requests, tokens

        if request.url.path.endswith("/token"):
            tokens += 1

            return httpx2.Response(200, json={"access_token": f"t{tokens}"})

        requests += 1

        return httpx2.Response(status)

    async with mock_client(handler, retry_delays=(0, 0)) as client:
        with pytest.raises(ApiError) as exc:
            await client.open_session(dev_eui="0000000000000001", slot_no=1, firmware_version="1", total_steps=1)

    assert exc.value.status == status and exc.value.stage == "verification"
    assert requests == tokens == (2 if status == 401 else 1)
