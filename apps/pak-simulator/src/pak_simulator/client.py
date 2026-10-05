"""HTTP client for the machine verification API, including OAuth and retries."""

import asyncio
import math
import time
from collections import deque
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Annotated

import httpx2
import msgspec
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
)

from pak_simulator.contracts import (
    SessionComplete,
    SessionOpen,
    SessionResponse,
    SessionResult,
    StepComplete,
    StepResponse,
    StepStart,
)
from pak_simulator.errors import ApiError, ClientError, ErrorStage, InvalidResponseError

_SESSIONS = "/verification/sessions"
_RETRY_STATUSES = frozenset({502, 503, 504})
_RETRY_DELAYS = (0.5, 1.0, 2.0, 4.0)
_TOKEN_MARGIN = 30.0
"""Seconds before expiry when the token is renewed."""


class _TokenResponse(msgspec.Struct, kw_only=True):
    access_token: Annotated[str, msgspec.Meta(min_length=1)]
    expires_in: Annotated[float, msgspec.Meta(gt=0)] = 3600


def _error(response: httpx2.Response, *, stage: ErrorStage = "verification") -> ApiError:
    try:
        body = response.json()
    except ValueError:
        body = None

    if not isinstance(body, dict):
        return ApiError(
            response.status_code,
            None,
            response.text[:200] or response.reason_phrase,
            stage=stage,
        )

    extra = body.get("extra")
    code = extra.get("code") if isinstance(extra, dict) else None

    if not isinstance(code, str) or not code:
        code = body.get("error")

    if not isinstance(code, str) or not code:
        code = None

    detail = body.get("detail") or body.get("error_description") or response.reason_phrase

    return ApiError(response.status_code, code, str(detail), stage=stage)


def _decode_response[T](
    response: httpx2.Response,
    response_type: type[T],
    *,
    stage: ErrorStage,
) -> T:
    try:
        return msgspec.json.decode(response.content, type=response_type)
    except msgspec.DecodeError as exc:
        raise InvalidResponseError(stage, exc) from exc


class PakClient:
    """Verification reports of one PAK, authenticated with its OAuth client credentials.

    The server answers a repeated report with the current state, so a request
    lost to the network or a gateway error is simply sent again.
    """

    def __init__(
        self,
        *,
        server: str,
        client_id: str,
        access_key: str,
        verify: bool,
        transport: httpx2.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        retry_delays: tuple[float, ...] = _RETRY_DELAYS,
    ) -> None:
        self._credentials = (client_id, access_key)
        # The token endpoint lives next to the reports, whatever issues the tokens.
        self._http = httpx2.AsyncClient(
            base_url=f"{server}/api/machine",
            timeout=15.0,
            verify=verify,
            transport=transport,
        )
        self._sleep = sleep
        self._retry_delays = retry_delays
        self._token: str | None = None
        self._token_expires = 0.0
        self._token_lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def authenticate(self) -> None:
        """Check the client credentials by requesting an OAuth access token."""
        await self._access_token()

    async def open_session(
        self,
        *,
        dev_eui: str,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> SessionResponse:
        response = await self._request(
            "POST",
            "",
            SessionOpen(
                dev_eui=dev_eui,
                slot_no=slot_no,
                firmware_version=firmware_version,
                total_steps=total_steps,
            ),
        )

        return _decode_response(response, SessionResponse, stage="verification")

    async def start_step(
        self,
        session_id: str,
        *,
        step_no: int,
        name: str,
        label: str,
        group: str,
    ) -> StepResponse:
        response = await self._request(
            "POST",
            f"/{session_id}/steps",
            StepStart(
                step_no=step_no,
                check_name=name,
                check_label=label,
                defect_group_code=group,
            ),
        )

        return _decode_response(response, StepResponse, stage="verification")

    async def complete_step(
        self,
        session_id: str,
        *,
        step_no: int,
        passed: bool,
        value: float | None,
        low: float | None,
        high: float | None,
        unit: str | None,
    ) -> StepResponse:
        response = await self._request(
            "PUT",
            f"/{session_id}/steps/{step_no}",
            StepComplete(
                status="passed" if passed else "failed",
                measurement_value=value,
                measurement_min=low,
                measurement_max=high,
                measurement_unit=unit,
            ),
        )

        return _decode_response(response, StepResponse, stage="verification")

    async def complete_session(self, session_id: str, result: SessionResult) -> SessionResponse:
        response = await self._request(
            "POST",
            f"/{session_id}/complete",
            SessionComplete(status=result),
        )

        return _decode_response(response, SessionResponse, stage="verification")

    async def _request(
        self,
        method: str,
        path: str,
        body: SessionOpen | StepStart | StepComplete | SessionComplete | None = None,
    ) -> httpx2.Response:
        renewed = False
        delays = deque(self._retry_delays)

        while True:
            token = await self._access_token()

            response = await self._retry_request(
                partial(
                    self._http.request,
                    method,
                    f"{_SESSIONS}{path}",
                    json=msgspec.to_builtins(body),
                    headers={"Authorization": f"Bearer {token}"},
                ),
                stage="verification",
                delays=delays,
            )

            # The token may have been revoked before it expired; renew it once.
            if response.status_code == 401 and not renewed:
                renewed = True
                self._forget_token(token)

                continue

            if response.is_error:
                raise _error(response)

            return response

    def _forget_token(self, token: str) -> None:
        # Another slot may have renewed it already.
        if self._token == token:
            self._token = None

    async def _access_token(self) -> str:
        async with self._token_lock:
            if self._token is not None and time.monotonic() < self._token_expires:
                return self._token

            try:
                response = await self._retry_request(
                    lambda: self._http.post(
                        "/token",
                        data={"grant_type": "client_credentials"},
                        auth=self._credentials,
                    ),
                    stage="authentication",
                    delays=deque(self._retry_delays),
                )
            except httpx2.TransportError as exc:
                raise ClientError("authentication", exc) from exc

            if response.is_error:
                raise _error(response, stage="authentication")

            payload = _decode_response(response, _TokenResponse, stage="authentication")

            if not payload.access_token.strip() or not math.isfinite(payload.expires_in):
                raise InvalidResponseError(
                    "authentication",
                    ValueError("Invalid access token or token lifetime"),
                )

            self._token = payload.access_token
            self._token_expires = time.monotonic() + payload.expires_in - min(_TOKEN_MARGIN, payload.expires_in / 2)

            return payload.access_token

    async def _retry_request(
        self,
        request: Callable[[], Awaitable[httpx2.Response]],
        *,
        stage: ErrorStage,
        delays: deque[float],
    ) -> httpx2.Response:
        async def invoke() -> httpx2.Response:
            return await request()

        def retryable(response: httpx2.Response) -> bool:
            return response.status_code in _RETRY_STATUSES and (
                stage != "authentication" or not _error(response, stage=stage).unauthorized
            )

        def consume_delay(_: RetryCallState) -> None:
            delays.popleft()

        def final_response(state: RetryCallState) -> httpx2.Response:
            assert state.outcome is not None
            # result() also propagates the original transport exception.
            response: httpx2.Response = state.outcome.result()

            return response

        retrying = AsyncRetrying(
            retry=retry_if_exception_type(httpx2.TransportError) | retry_if_result(retryable),
            stop=stop_after_attempt(len(delays) + 1),
            wait=lambda _: delays[0] if delays else 0,
            # Consume only when actually retrying. The remaining budget is
            # shared across a token refresh in _request().
            before_sleep=consume_delay,
            sleep=self._sleep,
            retry_error_callback=final_response,
        )
        response: httpx2.Response = await retrying(invoke)

        return response
