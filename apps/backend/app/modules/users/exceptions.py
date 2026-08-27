from app.core.exceptions import AppError


class UserError(AppError):
    """Base exception for user-management failures."""

    default_message = ""


class UserProvisioningError(UserError):
    """A user could not be provisioned consistently across its backing systems."""

    code = "user_provisioning_failed"


class UserNotFoundError(UserError):
    """The requested local user does not exist."""

    code = "user_not_found"
