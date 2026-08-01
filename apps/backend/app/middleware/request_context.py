import re
from time import perf_counter
from uuid import uuid4

from loguru import logger
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_MAX_LENGTH = 64
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")


def resolve_request_id(headers: Headers) -> str:
    request_ids = headers.getlist("x-request-id")

    if len(request_ids) == 1:
        request_id = request_ids[0]
        if (
            len(request_id) <= REQUEST_ID_MAX_LENGTH
            and REQUEST_ID_PATTERN.fullmatch(request_id) is not None
        ):
            return request_id

    return str(uuid4())


class RequestContextMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        quiet_path_prefixes: tuple[str, ...],
    ) -> None:
        self.app = app
        self.quiet_path_prefixes = quiet_path_prefixes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()

        request_id = resolve_request_id(Headers(scope=scope))

        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

                response_headers = MutableHeaders(scope=message)
                response_headers["x-request-id"] = request_id

            await send(message)

        with logger.contextualize(request_id=request_id):
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception:
                duration_ms = (perf_counter() - started_at) * 1000

                logger.bind(
                    event="http.request.failed",
                    method=scope["method"],
                    path=scope["path"],
                    status_code=500,
                    duration_ms=round(duration_ms, 2),
                ).exception("Http request failed")

                raise

            duration_ms = (perf_counter() - started_at) * 1000
            path = scope["path"]
            is_quiet_request = any(
                path == prefix or path.startswith(f"{prefix}/")
                for prefix in self.quiet_path_prefixes
            )
            log_level = "INFO"

            if is_quiet_request:
                log_level = (
                    "ERROR" if status_code >= 500 else "WARNING" if status_code >= 400 else "DEBUG"
                )

            logger.bind(
                event="http.request.completed",
                method=scope["method"],
                path=path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
            ).log(
                log_level,
                "{} {} -> {} in {:.2f} ms",
                scope["method"],
                path,
                status_code,
                duration_ms,
            )
