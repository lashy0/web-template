"""OpenAPI documentation of error responses."""

from __future__ import annotations

import msgspec
from litestar.openapi.datastructures import ResponseSpec


class ErrorExtra(msgspec.Struct):
    """Machine-readable details of an application error."""

    code: str


class ErrorResponse(msgspec.Struct):
    """Body of every error response (``litestar.exceptions.responses``).

    ``extra`` is present only for application errors that define a stable code.
    """

    status_code: int
    detail: str
    extra: ErrorExtra | None = None


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


__all__ = ("ErrorExtra", "ErrorResponse", "error_responses")
