from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class JsonOriginMiddleware:
    """Require JSON for body-bearing mutations and an allowed browser Origin."""

    def __init__(self, app: ASGIApp, *, allowed_origins: tuple[str, ...]) -> None:
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        content_type = headers.get("content-type", "").split(";", 1)[0]
        origin = headers.get("origin")
        content_length = headers.get("content-length")
        has_body = content_length not in {None, "0"} or headers.get("transfer-encoding") is not None
        if (
            scope["method"] in {"POST", "PUT", "PATCH"}
            and has_body
            and content_type != "application/json"
        ):
            response = JSONResponse(
                {
                    "code": "json_required",
                    "message": "JSON is required",
                    "request_id": scope.get("state", {}).get("request_id", ""),
                },
                415,
            )
            await response(scope, receive, send)
            return
        if origin is None or origin not in self.allowed_origins:
            response = JSONResponse(
                {
                    "code": "invalid_origin",
                    "message": "Origin is not allowed",
                    "request_id": scope.get("state", {}).get("request_id", ""),
                },
                403,
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
