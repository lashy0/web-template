from app.core.exceptions import AppError, DependencyUnavailableError, NotFoundError


class UserError(AppError):
    """Base exception for user-management failures."""

    default_message = ""


class UserProvisioningError(UserError, DependencyUnavailableError):
    """A user could not be provisioned consistently across its backing systems."""

    code = "user_provisioning_failed"


class UserNotFoundError(UserError, NotFoundError):
    """The requested local user does not exist."""

    code = "user_not_found"
