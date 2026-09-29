from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from advanced_alchemy.exceptions import NotFoundError
from litestar import Litestar, get
from litestar.di import NamedDependency, Provide
from litestar.exceptions import InternalServerException, NotFoundException, PermissionDeniedException
from litestar.testing import AsyncTestClient
from litestar.types import ExceptionHandlersMap
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.exc import OperationalError

from app.lib.exceptions import (
    ApplicationConflictError,
    ApplicationError,
    AuthorizationError,
    exception_group_to_http_response,
    exception_to_http_response,
)
from app.server.asgi import create_app

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
]


class _CommitConflictError(ApplicationConflictError):
    code = "commit_conflict"


async def _fail_after_handler() -> AsyncGenerator[None]:
    """Like ``provide_uow``: fails in the cleanup that runs after the handler."""
    yield
    raise _CommitConflictError


async def _finish_quietly() -> AsyncGenerator[None]:
    yield


async def _also_fail_after_handler() -> AsyncGenerator[None]:
    yield
    raise RuntimeError("second cleanup failed")


# With more than one generator dependency Litestar finishes them in a task
# group, so an error from their cleanup arrives wrapped in an ExceptionGroup.
@get(
    "/one-failure",
    dependencies={
        "failing": Provide(_fail_after_handler),
        "quiet": Provide(_finish_quietly),
    },
    sync_to_thread=False,
)
def _one_failure(failing: NamedDependency[None], quiet: NamedDependency[None]) -> None:
    return None


@get(
    "/two-failures",
    dependencies={
        "failing": Provide(_fail_after_handler),
        "also_failing": Provide(_also_fail_after_handler),
    },
    sync_to_thread=False,
)
def _two_failures(failing: NamedDependency[None], also_failing: NamedDependency[None]) -> None:
    return None


def _app_with_error_handlers() -> Litestar:
    handlers: ExceptionHandlersMap = {  # pyright: ignore[reportUnknownVariableType]
        ApplicationError: exception_to_http_response,
        ExceptionGroup: exception_group_to_http_response,
    }

    return Litestar(route_handlers=[_one_failure, _two_failures], exception_handlers=handlers)


async def test_exception_group_with_one_error_answers_as_that_error() -> None:
    async with AsyncTestClient(_app_with_error_handlers()) as client:
        response = await client.get("/one-failure")

    assert (response.status_code, response.json()["extra"]) == (409, {"code": "commit_conflict"})


async def test_exception_group_with_several_errors_is_server_error() -> None:
    async with AsyncTestClient(_app_with_error_handlers()) as client:
        response = await client.get("/two-failures")

    assert response.status_code == 500


def test_application_error_detail_defaults_to_message() -> None:
    assert ApplicationError("msg").detail == "msg"


def test_application_error_str_joins_message_and_detail() -> None:
    assert str(ApplicationError("msg", detail="detailed info")) == "msg detailed info"


def test_application_error_repr_names_class_and_detail() -> None:
    assert repr(ApplicationError(detail="detailed info")) == "ApplicationError - detailed info"


def test_exception_to_http_response_not_found() -> None:
    request = MagicMock()
    request.app.debug = False
    exc = NotFoundError("not found")

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, exc)

        args, _ = mock_create.call_args
        assert isinstance(args[1], NotFoundException)


def test_exception_to_http_response_auth_error() -> None:
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


def test_exception_to_http_response_debug() -> None:
    request = MagicMock()
    request.app.debug = True
    exc = ValueError("internal error")  # Will hit 'else' -> InternalServerException

    with patch("app.lib.exceptions.create_debug_response") as mock_debug:
        exception_to_http_response(request, exc)
        mock_debug.assert_called_once()
