"""Authorization errors usable by business contexts without auth coupling."""

from app.core.exceptions import NotFoundError, PermissionDeniedError


class ForbiddenError(PermissionDeniedError):
    code = "forbidden"
    default_message = ""


class IdentityNotFoundError(NotFoundError):
    code = "user_not_found"
    default_message = ""
