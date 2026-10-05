"""Shared English messages for machine API and connection failures."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import httpx2

ErrorStage = Literal["authentication", "verification", "health"]

_CODE_MESSAGES = {
    "invalid_client": "Authentication failed. Check the PAK client ID and access key.",
    "invalid_grant": "Authentication failed. The server rejected the credentials.",
    "unauthorized_client": "The PAK client is not allowed to obtain a token. Check its client permissions.",
    "unsupported_grant_type": "The server does not support the PAK authentication method. Check the backend version.",
    "invalid_scope": "The server rejected the requested access permissions. Check the PAK client configuration.",
    "invalid_request": "The authentication request was rejected. Check the server address and backend version.",
    "invalid_token": "The access token was rejected. Check the PAK status and credentials.",
    "access_denied": "Access denied. Check the PAK status and client permissions.",
    "temporarily_unavailable": "The authentication service is temporarily unavailable. Try again later.",
    "server_error": "The authentication service could not process the request. Check the server logs.",
    "verification_kg_not_found": "KG unit was not found. Check the configured DevEUI.",
    "verification_kg_scrapped": "This KG unit is scrapped and cannot be verified.",
    "verification_kg_packed": "This KG unit is packed or shipped and cannot be verified on an OTK-line PAK.",
    "verification_batch_archived": "This KG unit belongs to an archived batch and cannot be verified.",
    "verification_session_not_found": "The verification session was not found or is unavailable to this PAK.",
    "verification_session_already_running": "This unit already has an active verification session in another slot.",
    "verification_session_not_running": "The verification session has already finished and cannot accept results.",
    "verification_session_incomplete": "The session cannot finish: a check is still running or not all checks passed.",
    "verification_step_not_found": "The verification check was not found. Check the session and step sequence.",
    "verification_step_out_of_range": "The check number exceeds the session's configured number of steps.",
    "verification_step_already_exists": "This step number was already started with a different check.",
    "verification_step_in_progress": "The previous check is still running. Complete it before starting another.",
    "verification_step_already_completed": "This check was already completed with a different result.",
}

_STAGE_LABELS: dict[ErrorStage, str] = {
    "authentication": "Authentication failed",
    "verification": "Verification request failed",
    "health": "Server health check failed",
}


class ApiError(Exception):
    """An HTTP error, with the server's code and request stage preserved."""

    def __init__(self, status: int, code: str | None, detail: str, *, stage: ErrorStage = "verification") -> None:
        super().__init__(f"HTTP {status}: {code or detail}")
        self.status = status
        self.code = code
        self.detail = detail
        self.stage: ErrorStage = stage

    @property
    def unauthorized(self) -> bool:
        return self.status in {401, 403} or self.code in {
            "invalid_client",
            "invalid_grant",
            "invalid_token",
            "unauthorized_client",
            "access_denied",
        }


class ClientError(Exception):
    """A connection or response failure with the request stage preserved."""

    def __init__(self, stage: ErrorStage, cause: Exception) -> None:
        super().__init__(str(cause))
        self.stage: ErrorStage = stage
        self.cause = cause


class InvalidResponseError(ClientError):
    """The server response does not match the expected JSON contract."""


def file_error_message(exc: OSError, path: Path, *, action: Literal["read", "write"]) -> str:
    """Explain file failures without platform-specific or localized OS text."""
    if isinstance(exc, FileNotFoundError):
        reason = "the file or parent directory does not exist"
    elif isinstance(exc, PermissionError):
        reason = "permission denied; check access permissions and whether the file is in use"
    elif isinstance(exc, IsADirectoryError):
        reason = "the path points to a directory"
    else:
        reason = f"file operation failed (OS error {exc.errno})"

    return f"Cannot {action} {path}: {reason}."


def error_message(exc: Exception, *, stage: ErrorStage = "verification") -> str:
    """Explain a failure consistently in preflight, slot details and events."""
    if isinstance(exc, InvalidResponseError):
        prefix = _STAGE_LABELS[exc.stage]
        response = "an invalid token response" if exc.stage == "authentication" else "an invalid response"

        return f"{prefix}: the server returned {response}. Check the server address and backend version."

    if isinstance(exc, ClientError):
        stage, exc = exc.stage, exc.cause

    if isinstance(exc, ApiError):
        return _api_message(exc)

    prefix = _STAGE_LABELS[stage]

    if isinstance(exc, httpx2.TimeoutException | TimeoutError):
        return f"{prefix}: the server did not respond in time. Check connectivity and server availability."

    if isinstance(exc, httpx2.ConnectError):
        return f"{prefix}: could not connect to the server. Check the server address, connectivity and TLS settings."

    if isinstance(exc, httpx2.TransportError):
        return f"{prefix}: the connection failed. Check connectivity and server availability."

    raise exc


def _api_message(exc: ApiError) -> str:
    if exc.code in _CODE_MESSAGES:
        return _CODE_MESSAGES[exc.code]

    prefix = _STAGE_LABELS[exc.stage]

    if exc.status == 401:
        message = (
            "Check the PAK client ID and access key."
            if exc.stage == "authentication"
            else "The access token was rejected. Check the PAK status and credentials."
        )
    elif exc.status == 403:
        message = "Access denied. Check the PAK status and client permissions."
    elif exc.status == 404:
        message = (
            "The authentication endpoint was not found. Check the server address and routing."
            if exc.stage == "authentication"
            else "The requested endpoint or resource was not found. Check the server address and backend version."
        )
    elif exc.status == 429:
        message = "Too many requests. Wait before trying again."
    elif exc.status >= 500:
        message = "The server could not process the request. Check server availability and logs."
    else:
        message = "The server rejected the request. Check the configuration and backend version."

    diagnostic = f"HTTP {exc.status}" + (f"; {exc.code}" if exc.code else "")
    detail = " ".join(exc.detail.split())[:200]

    return f"{prefix}: {message} ({diagnostic})" + (f" {detail}" if detail else "")
