from app.core.exceptions import AppError, DependencyUnavailableError, NotFoundError


class UserError(AppError):
    default_message = ""


class UserProvisioningError(UserError, DependencyUnavailableError):
    code = "user_provisioning_failed"


class UserNotFoundError(UserError, NotFoundError):
    code = "user_not_found"
