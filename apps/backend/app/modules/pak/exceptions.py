from app.core.exceptions import AppError


class PakError(AppError):
    """Base exception for PAK domain failures."""

    default_message = ""


class PakNotFoundError(PakError):
    """The requested PAK does not exist."""

    code = "pak_not_found"


class PakAlreadyExistsError(PakError):
    """A PAK with the same identifier already exists."""

    code = "pak_already_exists"


class PakProvisioningError(PakError):
    """A PAK could not be provisioned consistently across its backing systems."""

    code = "pak_provisioning_failed"


class PakAccessKeyConfigurationError(PakError):
    """The service cannot safely encrypt or decrypt PAK access keys."""

    code = "pak_access_key_configuration_error"


class InvalidMachineAccessTokenError(PakError):
    """A machine access token is missing, invalid, or does not identify a PAK."""

    code = "invalid_machine_access_token"
