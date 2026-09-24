"""Application exception types and their translation into HTTP responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from advanced_alchemy.exceptions import IntegrityError, NotFoundError
from litestar.exceptions import (
    ClientException,
    HTTPException,
    InternalServerException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
    ServiceUnavailableException,
)
from litestar.exceptions.responses import (
    create_debug_response as _create_debug_response,  # pyright: ignore[reportUnknownVariableType]
)
from litestar.exceptions.responses import (
    create_exception_response as _create_exception_response,  # pyright: ignore[reportUnknownVariableType]
)
from litestar.status_codes import HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR
from loguru import logger
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.exc import SQLAlchemyError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from litestar.connection import Request
    from litestar.response import Response


class ApplicationError(Exception):
    """Base exception type for the lib's custom exception types."""

    detail: str
    code: str | None = None
    """Stable machine-readable error code, sent to clients as ``extra.code``."""

    def __init__(
        self,
        *args: Any,
        detail: str = "",
        code: str | None = None,
    ) -> None:
        """Initialize ``AdvancedAlchemyException``.

        Args:
            *args: args are converted to :class:`str` before passing to :class:`Exception`
            detail: detail of the exception.
            code: overrides the class-level error code.
        """
        str_args = [str(arg) for arg in args if arg]

        if not detail:
            if str_args:
                detail, *str_args = str_args
            elif hasattr(self, "detail"):
                detail = self.detail

        self.detail = detail

        if code is not None:
            self.code = code

        super().__init__(*str_args)

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"

        return self.__class__.__name__

    def __str__(self) -> str:
        return " ".join((*self.args, self.detail)).strip()


class ApplicationClientError(ApplicationError):
    """Base exception type for client errors (HTTP 400)."""


class AuthenticationError(ApplicationClientError):
    """The caller's credentials are missing or invalid (HTTP 401)."""


class AuthorizationError(ApplicationClientError):
    """A user tried to do something they shouldn't have (HTTP 403)."""


class ApplicationNotFoundError(ApplicationClientError):
    """A resource outside the database, e.g. in Kratos or Hydra, does not exist (HTTP 404)."""


class ApplicationConflictError(ApplicationClientError):
    """The request conflicts with the current state of a resource (HTTP 409)."""


class ServiceUnavailableError(ApplicationError):
    """An external service required by the request is unavailable (HTTP 503)."""


class _HTTPConflictException(HTTPException):
    """Request conflict with the current state of the target resource."""

    status_code = HTTP_409_CONFLICT


_create_debug_response_typed = cast("Callable[[Any, Exception], Any]", _create_debug_response)
_create_exception_response_typed = cast("Callable[[Any, HTTPException], Any]", _create_exception_response)


def create_debug_response(request: Request[Any, Any, Any], exc: Exception) -> Response[Any]:
    return cast("Response[Any]", _create_debug_response_typed(request, exc))


def create_exception_response(request: Request[Any, Any, Any], exc: HTTPException) -> Response[Any]:
    return cast("Response[Any]", _create_exception_response_typed(request, exc))


def _is_database_fault(exc: Exception) -> bool:
    """Whether Advanced Alchemy wrapped a non-constraint database error.

    ``wrap_sqlalchemy_exception`` raises ``IntegrityError`` for every
    ``StatementError``, including ``OperationalError`` (lost connection,
    deadlock). Only a real constraint violation is a conflict. The whole cause
    chain is checked because services re-raise wrapped errors as domain
    conflict errors (``raise PakDeviceCodeTakenError from error``); an error
    without a database cause is a conflict the application detected itself.
    """
    cause = exc.__cause__

    while cause is not None:
        if isinstance(cause, SQLAlchemyError):
            return not isinstance(cause, SQLAlchemyIntegrityError)

        cause = cause.__cause__

    return False


def _http_exception_type(exc: Exception) -> type[HTTPException]:
    if isinstance(exc, NotFoundError | ApplicationNotFoundError):
        return NotFoundException

    # Server faults such as a lost connection must not look like 409.
    if isinstance(exc, IntegrityError | ApplicationConflictError) and _is_database_fault(exc):
        return InternalServerException

    # Covers DuplicateKeyError and ForeignKeyError.
    if isinstance(exc, IntegrityError | ApplicationConflictError):
        return _HTTPConflictException

    if isinstance(exc, AuthenticationError):
        return NotAuthorizedException

    if isinstance(exc, AuthorizationError):
        return PermissionDeniedException

    if isinstance(exc, ApplicationClientError):
        return ClientException

    if isinstance(exc, ServiceUnavailableError):
        return ServiceUnavailableException

    return InternalServerException


def exception_to_http_response(request: Request[Any, Any, Any], exc: Exception) -> Response[Any]:
    """Transform application and repository exceptions to HTTP responses.

    Client errors expose the exception detail. Server errors are logged and,
    outside debug mode, answered with a generic detail so that SQL fragments or
    upstream responses never reach the client.

    Args:
        request: The request that experienced the exception.
        exc: Exception raised during handling of the request.

    Returns:
        Exception response appropriate to the type of original exception.
    """
    http_exc = _http_exception_type(exc)

    if http_exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        logger.bind(
            method=request.method,
            path=request.url.path,
            status_code=http_exc.status_code,
        ).opt(exception=exc).error("Request failed with a server error.")

        if request.app.debug:
            return create_debug_response(request, exc)

        return create_exception_response(request, http_exc())

    detail = getattr(exc, "detail", "") or str(exc)
    code = exc.code if isinstance(exc, ApplicationError) else None
    extra = {"code": code} if code else None

    return create_exception_response(request, http_exc(detail=detail, extra=extra))


def _leaf_exceptions(group: BaseExceptionGroup[Any]) -> list[BaseException]:
    leaves: list[BaseException] = []
    pending: list[BaseException] = list(group.exceptions)

    while pending:
        exc = pending.pop(0)

        if isinstance(exc, BaseExceptionGroup):
            pending[:0] = cast("tuple[BaseException, ...]", exc.exceptions)
        else:
            leaves.append(exc)

    return leaves


def exception_group_to_http_response(
    request: Request[Any, Any, Any],
    exc: ExceptionGroup[Exception],
) -> Response[Any]:
    """Unwrap errors raised while Litestar cleans up ``yield`` dependencies.

    With more than one generator dependency, Litestar finishes them in an
    ``anyio`` task group, so an error from any of them (for example a failed
    commit in ``provide_uow``) arrives wrapped in an ``ExceptionGroup`` that no
    type-based handler matches. A single wrapped error is dispatched to the
    handler that would have handled it unwrapped; several errors are a server
    fault.
    """
    leaves = _leaf_exceptions(exc)

    if len(leaves) != 1 or not isinstance(leaves[0], Exception):
        return exception_to_http_response(request, exc)

    leaf = leaves[0]
    handlers = cast(
        "Mapping[object, Callable[[Request[Any, Any, Any], Exception], Response[Any]]]",
        request.route_handler.resolve_exception_handlers(),  # pyright: ignore[reportUnknownMemberType]
    )

    for exc_type in type(leaf).__mro__:
        if (handler := handlers.get(exc_type)) is not None:
            return handler(request, leaf)

    if isinstance(leaf, HTTPException):
        return create_exception_response(request, leaf)

    return exception_to_http_response(request, leaf)


__all__ = (
    "ApplicationClientError",
    "ApplicationConflictError",
    "ApplicationError",
    "ApplicationNotFoundError",
    "AuthenticationError",
    "AuthorizationError",
    "ServiceUnavailableError",
    "exception_group_to_http_response",
    "exception_to_http_response",
)
