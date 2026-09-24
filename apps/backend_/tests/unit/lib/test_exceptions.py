from unittest.mock import MagicMock, patch

import pytest
from advanced_alchemy.exceptions import NotFoundError
from litestar.exceptions import NotFoundException, PermissionDeniedException

from app.lib.exceptions import (
    ApplicationError,
    AuthorizationError,
    exception_to_http_response,
)

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
]


def test_application_error_init() -> None:
    exc = ApplicationError("msg", detail="detailed info")
    assert exc.detail == "detailed info"
    assert "msg" in str(exc)
    assert "detailed info" in str(exc)

    exc2 = ApplicationError("msg")
    assert exc2.detail == "msg"

    assert "ApplicationError" in repr(exc)


async def test_exception_to_http_response_not_found() -> None:
    request = MagicMock()
    request.app.debug = False
    exc = NotFoundError("not found")

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, exc)

        args, _ = mock_create.call_args
        assert isinstance(args[1], NotFoundException)


async def test_exception_to_http_response_auth_error() -> None:
    request = MagicMock()
    request.app.debug = False
    exc = AuthorizationError("unauthorized")

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, exc)

        args, _ = mock_create.call_args
        assert isinstance(args[1], PermissionDeniedException)


async def test_exception_to_http_response_debug() -> None:
    request = MagicMock()
    request.app.debug = True
    exc = ValueError("internal error")  # Will hit 'else' -> InternalServerException

    with patch("app.lib.exceptions.create_debug_response") as mock_debug:
        exception_to_http_response(request, exc)
        mock_debug.assert_called_once()
