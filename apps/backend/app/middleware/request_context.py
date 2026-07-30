from time import perf_counter
from uuid import uuid4

from loguru import logger
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


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

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id", str(uuid4()))

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
