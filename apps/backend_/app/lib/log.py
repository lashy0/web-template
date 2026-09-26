"""Structured logging: renderers, the per-request log line and exception logging."""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import structlog
from advanced_alchemy.exceptions import RepositoryError
from litestar.datastructures import MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.exceptions import HTTPException
from litestar.logging.config import StructlogEventFilter
from litestar.middleware import ASGIMiddleware
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from structlog.dev import (
    BRIGHT,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET_ALL,
    YELLOW,
    Column,
    ConsoleRenderer,
    KeyValueColumnFormatter,
    RichTracebackFormatter,
)

from app.lib.exceptions import ApplicationError

if TYPE_CHECKING:
    from litestar.types import ASGIApp, HTTPScope, Logger, Message, Receive, Scope, Send
    from structlog.typing import EventDict, Processor, WrappedLogger

logger = structlog.get_logger()

REQUEST_ID_HEADER = "x-request-id"
_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

_QUIET_PATH = re.compile(r"/health|/schema(/.*)?")
"""Health checks polled by orchestrators and the API docs: successful requests are logged at debug level only."""

_CONSOLE_LEVELS = {"warning": "WARN", "critical": "CRIT", "exception": "ERROR"}
_CONSOLE_REQUEST_ID_LENGTH = 8
_CONSOLE_SOURCE_WIDTH = 10
_CONSOLE_STATUS_STYLES: dict[int, str] = {1: DIM, 2: GREEN, 3: CYAN, 4: YELLOW, 5: RED}


def _source(logger_name: str) -> str:
    # "litestar_autowire.plugin" -> "autowire", "sqlalchemy.engine.Engine" -> "sqlalchemy".
    package = logger_name.split(".", 1)[0].lstrip("_")
    package = package.removeprefix("litestar_") or package

    return package[:_CONSOLE_SOURCE_WIDTH]


def _status_style(status_code: int) -> str:
    return _CONSOLE_STATUS_STYLES[min(status_code // 100, 5)]


def _duration(duration_ms: float) -> str:
    if duration_ms < 10:
        return f"{duration_ms:.1f}ms"

    if duration_ms < 1000:
        return f"{duration_ms:.0f}ms"

    return f"{duration_ms / 1000:.2f}s"


def _request_line(event_dict: EventDict) -> str:
    # Fixed-width columns first and the path last, so a long path shifts nothing.
    status_code = event_dict.pop("status_code")
    request_id = str(event_dict.pop("request_id", ""))[:_CONSOLE_REQUEST_ID_LENGTH]

    return (
        f"{event_dict.pop('method'):<7} {_status_style(status_code)}{status_code}{RESET_ALL}{BRIGHT} "
        f"{_duration(event_dict.pop('duration_ms')):>6}  {event_dict.pop('path'):<40}"
        f"{RESET_ALL} {DIM}{request_id}{RESET_ALL}"
    )


def _console_fields(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """Shape an event for a terminal: its source, a compact request line, a short request ID."""
    logger_name = event_dict.pop("logger", None)
    event_dict["source"] = _source(logger_name) if logger_name else "app"

    if event_dict.get("event") == "http.request":
        event_dict["source"] = "http"
        event_dict["event"] = _request_line(event_dict)

    if isinstance(request_id := event_dict.get("request_id"), str):
        event_dict["request_id"] = request_id[:_CONSOLE_REQUEST_ID_LENGTH]

    return event_dict


def _console_renderer() -> ConsoleRenderer:
    level_styles = ConsoleRenderer.get_default_level_styles(colors=True)

    def level(key: str, value: object) -> str:  # noqa: ARG001 - the ColumnFormatter signature
        name = str(value)
        return f"{level_styles.get(name, '')}{BRIGHT}{_CONSOLE_LEVELS.get(name, name.upper()):<5}{RESET_ALL}"

    def text(style: str, width: int = 0) -> KeyValueColumnFormatter:
        return KeyValueColumnFormatter(
            key_style=None, value_style=style, reset_style=RESET_ALL, value_repr=str, width=width
        )

    return ConsoleRenderer(
        colors=True,
        exception_formatter=RichTracebackFormatter(show_locals=False, width=120),
        columns=[
            Column("timestamp", text(DIM)),
            Column("level", level),
            Column("source", text(CYAN, width=_CONSOLE_SOURCE_WIDTH)),
            Column("event", text(BRIGHT)),
            Column("", KeyValueColumnFormatter(key_style=DIM, value_style="", reset_style=RESET_ALL, value_repr=str)),
        ],
    )


def _output(*, as_json: bool) -> list[Processor]:
    if as_json:
        # Values JSON cannot represent are written with repr() instead of failing the call that logs them.
        return [
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    return [
        structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=True),
        _console_fields,
        _console_renderer(),
    ]


def structlog_processors(*, as_json: bool) -> list[Processor]:
    """Processors of the application's own events: context of the request, level, time, rendering."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        *_output(as_json=as_json),
    ]


def stdlib_processors(*, as_json: bool) -> list[Processor]:
    """Processors of records from standard ``logging``: SQLAlchemy, SAQ, uvicorn, Litestar.

    They are rendered on the queue listener thread, where the request context
    is not available, so these records carry no ``request_id``.
    """
    return [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        StructlogEventFilter(["color_message", "message"]),
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        *_output(as_json=as_json),
    ]


def log_unhandled_exception(logger: Logger, scope: Scope, _traceback: list[str]) -> None:
    """Log an exception that became a server error without passing through ``exception_to_http_response``.

    Litestar calls this for every exception a handler raises, client errors
    included. Application and repository errors are logged by their handler,
    so only unexpected exceptions and server HTTP errors are logged here.
    """
    exc = sys.exc_info()[1]

    if isinstance(exc, ApplicationError | RepositoryError | ExceptionGroup):
        return

    if isinstance(exc, HTTPException) and exc.status_code < HTTP_500_INTERNAL_SERVER_ERROR:
        return

    logger.error("http.unhandled_exception", path=scope["path"], exc_info=exc)


_REQUEST_STATE = "request_log"


@dataclass(slots=True)
class _RequestState:
    request_id: str
    started: float
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR


def _request_id(scope: Scope) -> str:
    # A proxy may already have tagged the request; anything unexpected is replaced.
    for name, value in scope["headers"]:
        if name == REQUEST_ID_HEADER.encode():
            incoming = value.decode("latin-1")

            if _REQUEST_ID.fullmatch(incoming):
                return incoming

    return uuid4().hex


class RequestContextMiddleware(ASGIMiddleware):
    """Give every HTTP request an ID that tags all of its records.

    The ID comes from the ``X-Request-ID`` header when a proxy set one.
    ``log_request`` returns it in the response and writes the request line.
    """

    scopes = (ScopeType.HTTP,)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        request_id = _request_id(scope)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        scope["state"][_REQUEST_STATE] = _RequestState(request_id=request_id, started=perf_counter())

        await next_app(scope, receive, send)


def _request_level(method: str, path: str, status_code: int) -> int:
    if status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        return logging.ERROR

    # CORS preflights precede every cross-origin call and say nothing of their own.
    if status_code < HTTP_400_BAD_REQUEST and (method == "OPTIONS" or _QUIET_PATH.fullmatch(path)):
        return logging.DEBUG

    return logging.INFO


async def log_request(message: Message, scope: Scope) -> None:
    """Return the request ID and write one line per request once its response is sent.

    A ``before_send`` hook rather than part of the middleware: errors raised by
    middleware (401 from authentication) become responses outside every
    middleware, but every response passes this hook. Headers, cookies and
    bodies are not logged, so no secret reaches the log.
    """
    state: _RequestState | None = scope["state"].get(_REQUEST_STATE)

    if state is None:
        return

    if message["type"] == "http.response.start":
        state.status_code = message["status"]
        MutableScopeHeaders.from_message(message)[REQUEST_ID_HEADER] = state.request_id
    elif message["type"] == "http.response.body" and not message.get("more_body", False):
        del scope["state"][_REQUEST_STATE]
        method = cast("HTTPScope", scope)["method"]
        level = _request_level(method, scope["path"], state.status_code)
        logger.log(
            level,
            "http.request",
            method=method,
            path=scope["path"],
            status_code=state.status_code,
            duration_ms=round((perf_counter() - state.started) * 1000, 1),
        )
        structlog.contextvars.clear_contextvars()


__all__ = (
    "RequestContextMiddleware",
    "log_request",
    "log_unhandled_exception",
    "stdlib_processors",
    "structlog_processors",
)
