from __future__ import annotations

import asyncio
import json

import httpx2
import pytest

from pak_simulator.errors import InvalidResponseError
from tests.unit.support import TEST_TIMEOUT, mock_client

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


async def test_slots_share_one_token() -> None:
    token_requests = 0

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal token_requests

        if request.url.path.endswith("/token"):
            token_requests += 1
            await asyncio.sleep(0)

            return httpx2.Response(200, json={"access_token": "token"})

        return httpx2.Response(201, json={"id": "session", "firmwareVersion": "1", "totalSteps": 1})

    async with mock_client(handler) as client:
        async with asyncio.timeout(TEST_TIMEOUT):
            await asyncio.gather(
                *(
                    client.open_session(dev_eui=f"{slot:016X}", slot_no=slot, firmware_version="1", total_steps=1)
                    for slot in range(1, 7)
                )
            )

    assert token_requests == 1


async def test_short_lifetime_token_is_cached() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        assert request.url.path.endswith("/token")

        return httpx2.Response(200, json={"access_token": "token", "expires_in": 10})

    async with mock_client(handler) as client:
        await client.authenticate()
        await client.authenticate()

    assert len(requests) == 1


async def test_revoked_token_is_renewed_once() -> None:
    tokens = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/token"):
            tokens.append("token")

            return httpx2.Response(200, json={"access_token": f"t{len(tokens)}", "expires_in": 3600})

        if request.headers["Authorization"] == "Bearer t1":
            return httpx2.Response(401)

        return httpx2.Response(200, json={"id": "session", **json.loads(request.content)})

    async with mock_client(handler) as client:
        await client.open_session(dev_eui="0000000000000001", slot_no=1, firmware_version="1", total_steps=1)

    assert len(tokens) == 2


@pytest.mark.parametrize("payload", [{"access_token": " "}, {"access_token": "t", "expires_in": "bad"}])
async def test_invalid_token_response_rejected(payload: dict[str, object]) -> None:
    async with mock_client(lambda _: httpx2.Response(200, json=payload)) as client:
        with pytest.raises(InvalidResponseError):
            await client.authenticate()


async def test_measurement_payload_uses_wire_names() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)

        if request.url.path.endswith("/token"):
            return httpx2.Response(200, json={"access_token": "token"})

        return httpx2.Response(200, json={"id": "step", "stepNo": 1})

    async with mock_client(handler) as client:
        await client.complete_step("session", step_no=1, passed=False, value=3, low=4, high=5, unit="mA")

    assert requests[-1].method == "PUT"
    assert requests[-1].url.path == "/api/machine/verification/sessions/session/steps/1"
    assert json.loads(requests[-1].content) == {
        "status": "failed",
        "measurementValue": 3,
        "measurementMin": 4,
        "measurementMax": 5,
        "measurementUnit": "mA",
    }


async def test_session_requests_use_wire_names_and_decode_responses() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/token"):
            return httpx2.Response(200, json={"access_token": "token"})

        requests.append(request)

        return httpx2.Response(
            200, json={"id": "existing-session", "firmwareVersion": "old", "totalSteps": 3, "completedSteps": 1}
        )

    async with mock_client(handler) as client:
        session = await client.open_session(dev_eui="0000000000000001", slot_no=2, firmware_version="1", total_steps=4)
        completed = await client.complete_session(session.id, "aborted")

    assert (session.id, session.firmware_version, session.total_steps, session.completed_steps) == (
        "existing-session",
        "old",
        3,
        1,
    )
    assert completed == session
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/api/machine/verification/sessions"),
        ("POST", "/api/machine/verification/sessions/existing-session/complete"),
    ]
    assert [json.loads(request.content) for request in requests] == [
        {"devEui": "0000000000000001", "slotNo": 2, "firmwareVersion": "1", "totalSteps": 4},
        {"status": "aborted"},
    ]
    assert all(request.headers["Authorization"] == "Bearer token" for request in requests)


async def test_start_step_uses_wire_names_and_decodes_response() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/token"):
            return httpx2.Response(200, json={"access_token": "token"})

        requests.append(request)

        return httpx2.Response(201, json={"id": "server-step", "stepNo": 2})

    async with mock_client(handler) as client:
        step = await client.start_step("session", step_no=2, name="current", label="Current", group="POWER")

    assert (step.id, step.step_no) == ("server-step", 2)
    assert len(requests) == 1
    assert (requests[0].method, requests[0].url.path) == (
        "POST",
        "/api/machine/verification/sessions/session/steps",
    )
    assert json.loads(requests[0].content) == {
        "stepNo": 2,
        "checkName": "current",
        "checkLabel": "Current",
        "defectGroupCode": "POWER",
    }


@pytest.mark.parametrize("field, value", [("firmwareVersion", None), ("totalSteps", None), ("totalSteps", 0)])
async def test_session_response_requires_valid_reuse_parameters(field: str, value: object) -> None:
    payload: dict[str, object] = {"id": "session", "firmwareVersion": "1", "totalSteps": 3}

    if value is None:
        del payload[field]
    else:
        payload[field] = value

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/token"):
            return httpx2.Response(200, json={"access_token": "token"})

        return httpx2.Response(200, json=payload)

    async with mock_client(handler) as client:
        with pytest.raises(InvalidResponseError) as exc_info:
            await client.open_session(dev_eui="0000000000000001", slot_no=1, firmware_version="1", total_steps=3)

    assert exc_info.value.stage == "verification"
    assert field in str(exc_info.value.cause)
