"""Account domain errors with stable client-facing codes."""

from app.lib.exceptions import ApplicationConflictError, AuthorizationError


class UserArchivedError(ApplicationConflictError):
    """The user is archived and cannot be modified (HTTP 409)."""

    code = "user_archived"
    detail = "Archived user cannot be modified."


class LastAdministratorError(ApplicationConflictError):
    """The change would leave no active administrator (HTTP 409)."""

    code = "last_administrator"
    detail = "At least one active administrator must remain."


class SelfActionForbiddenError(AuthorizationError):
    """An administrator tried to lock themselves out (HTTP 403).

    The detail names the refused action, for example deactivating or archiving
    one's own account.
    """

    code = "self_action_forbidden"
    detail = "You cannot perform this action on your own account."


__all__ = ("LastAdministratorError", "SelfActionForbiddenError", "UserArchivedError")
