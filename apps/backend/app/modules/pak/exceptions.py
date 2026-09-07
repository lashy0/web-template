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
    """The requested PAK does not exist."""

    code = "pak_not_found"


class PakAlreadyExistsError(PakError, ConflictError):
    """A PAK with the same identifier already exists."""

    code = "pak_already_exists"


class PakProvisioningError(PakError, DependencyUnavailableError):
    """A PAK could not be provisioned consistently across its backing systems."""

    code = "pak_provisioning_failed"


class PakCredentialSynchronizationError(PakError, DependencyUnavailableError):
    """Hydra rotated a secret but the encrypted local recovery copy was not saved."""

    code = "pak_credentials_out_of_sync"


class PakDeletionSynchronizationError(PakError, DependencyUnavailableError):
    """Hydra deleted a client but the local PAK projection was not removed."""

    code = "pak_deletion_out_of_sync"


class PakAccessKeyConfigurationError(PakError, DependencyUnavailableError):
    """The service cannot safely encrypt or decrypt PAK access keys."""

    code = "pak_access_key_configuration_error"


class InvalidMachineAccessTokenError(PakError, UnauthenticatedError):
    """A machine access token is missing, invalid, or does not identify a PAK."""

    code = "invalid_machine_access_token"


class PakCannotBeDeletedError(PakError, ConflictError):
    """The PAK cannot be deleted because it has verification history."""

    code = "pak_cannot_be_deleted"


class PakTestNotFoundError(PakError, NotFoundError):
    """The requested PAK test does not exist."""

    code = "pak_test_not_found"


class PakTestConfigurationError(PakError, ConflictError):
    """A PAK test references an invalid defect configuration."""

    code = "pak_test_configuration_error"
