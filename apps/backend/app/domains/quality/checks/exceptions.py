from app.core.exceptions import ConflictError, NotFoundError


class CheckNotFoundError(NotFoundError):
    code = "pak_test_not_found"


class CheckConfigurationError(ConflictError):
    code = "pak_test_configuration_error"
