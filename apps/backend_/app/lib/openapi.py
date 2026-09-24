"""OpenAPI documentation of error responses."""

from __future__ import annotations

import msgspec
from litestar.openapi.datastructures import ResponseSpec


class ErrorResponse(msgspec.Struct):
    """Body of every error response (``litestar.exceptions.responses``)."""

    status_code: int
    detail: str


_DESCRIPTIONS = {
    401: "Authentication is missing or invalid.",
    403: "The authenticated user lacks the required permission or may not act on this target.",
    404: "The resource does not exist.",
    409: "The request conflicts with the current state of the resource.",
    503: "An identity provider required by the request is unavailable.",
}


def error_responses(*status_codes: int) -> dict[int, ResponseSpec]:
    """Describe error responses for a route handler's ``responses`` argument."""
    return {
        status_code: ResponseSpec(
            data_container=ErrorResponse,
            description=_DESCRIPTIONS[status_code],
            generate_examples=False,
        )
        for status_code in status_codes
    }


__all__ = ("ErrorResponse", "error_responses")
