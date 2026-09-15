from app.core.exceptions import (
    AppError,
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    UnauthenticatedError,
)


class PakError(AppError):
    """Base exception for PAK domain failures."""

    default_message = ""


class PakNotFoundError(PakError, NotFoundError):
    code = "pak_not_found"


class PakAlreadyExistsError(PakError, ConflictError):
    code = "pak_already_exists"


class PakProvisioningError(PakError, DependencyUnavailableError):
    code = "pak_provisioning_failed"


class PakCredentialSynchronizationError(PakError, DependencyUnavailableError):
    code = "pak_credentials_out_of_sync"


class PakDeletionSynchronizationError(PakError, DependencyUnavailableError):
    code = "pak_deletion_out_of_sync"


class PakAccessKeyConfigurationError(PakError, DependencyUnavailableError):
    code = "pak_access_key_configuration_error"


class InvalidMachineAccessTokenError(PakError, UnauthenticatedError):
    code = "invalid_machine_access_token"


class PakCannotBeDeletedError(PakError, ConflictError):
    code = "pak_cannot_be_deleted"
