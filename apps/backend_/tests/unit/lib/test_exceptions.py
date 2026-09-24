from unittest.mock import MagicMock, patch

import pytest
from advanced_alchemy.exceptions import NotFoundError
from litestar.exceptions import InternalServerException, NotFoundException, PermissionDeniedException
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.exc import OperationalError

from app.lib.exceptions import (
    ApplicationConflictError,
    ApplicationError,
    AuthorizationError,
    exception_to_http_response,
)
from app.server.asgi import create_app

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


def test_exception_to_http_response_includes_error_code() -> None:
    class ArchivedError(ApplicationConflictError):
        code = "resource_archived"

    request = MagicMock()
    request.app.debug = False

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, ArchivedError(detail="Archived."))

    assert mock_create.call_args.args[1].extra == {"code": "resource_archived"}


def test_exception_to_http_response_omits_missing_error_code() -> None:
    request = MagicMock()
    request.app.debug = False

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, ApplicationConflictError(detail="Conflict."))

    assert mock_create.call_args.args[1].extra is None


def _conflict_caused_by(cause: Exception) -> ApplicationConflictError:
    try:
        raise ApplicationConflictError(detail="Conflict.") from cause
    except ApplicationConflictError as exc:
        return exc


def test_exception_to_http_response_conflict_from_constraint_is_409() -> None:
    request = MagicMock()
    request.app.debug = False
    exc = _conflict_caused_by(SQLAlchemyIntegrityError("INSERT", {}, Exception("duplicate key")))

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, exc)

    assert mock_create.call_args.args[1].status_code == 409


def test_exception_to_http_response_conflict_from_lost_connection_is_500() -> None:
    request = MagicMock()
    request.app.debug = False
    exc = _conflict_caused_by(OperationalError("INSERT", {}, Exception("connection lost")))

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, exc)

    assert isinstance(mock_create.call_args.args[1], InternalServerException)


def test_error_codes_are_unique() -> None:
    create_app()  # imports every domain, so all error classes are defined
    pending: list[type[ApplicationError]] = [ApplicationError]
    codes: list[str] = []

    while pending:
        error_type = pending.pop()
        pending.extend(error_type.__subclasses__())

        if error_type.code is not None and "code" in vars(error_type):
            codes.append(error_type.code)

    assert len(codes) == len(set(codes))


def test_application_error_code_overrides_class_code() -> None:
    exc = ApplicationConflictError(detail="Conflict.", code="custom_conflict")

    assert exc.code == "custom_conflict"


async def test_exception_to_http_response_debug() -> None:
    request = MagicMock()
    request.app.debug = True
    exc = ValueError("internal error")  # Will hit 'else' -> InternalServerException

    with patch("app.lib.exceptions.create_debug_response") as mock_debug:
        exception_to_http_response(request, exc)
        mock_debug.assert_called_once()
