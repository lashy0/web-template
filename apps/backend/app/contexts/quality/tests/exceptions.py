from app.core.exceptions import ConflictError, NotFoundError


class PakTestNotFoundError(NotFoundError):
    code = "pak_test_not_found"


class PakTestConfigurationError(ConflictError):
    code = "pak_test_configuration_error"
