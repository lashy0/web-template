"""PAK domain errors with stable client-facing codes."""

from app.lib.exceptions import ApplicationConflictError


class PakDeviceArchivedError(ApplicationConflictError):
    """The PAK device is archived and cannot be modified (HTTP 409)."""

    code = "pak_device_archived"
    detail = "Archived PAK device cannot be modified."


class PakDeviceCodeTakenError(ApplicationConflictError):
    """Another PAK device already uses the code (HTTP 409)."""

    code = "pak_device_code_taken"
    detail = "PAK device code is already registered."


class PakDeviceInUseError(ApplicationConflictError):
    """The PAK device ran verification sessions, so it cannot be deleted (HTTP 409)."""

    code = "pak_in_use"
    detail = "PAK device has verification history; archive it instead."


class PakVerificationRunningError(ApplicationConflictError):
    """The PAK is verifying KG units, so its key may only be replaced immediately (HTTP 409)."""

    code = "pak_verification_running"
    detail = "PAK device is running a verification; replace its key immediately or wait for the end."


__all__ = (
    "PakDeviceArchivedError",
    "PakDeviceCodeTakenError",
    "PakDeviceInUseError",
    "PakVerificationRunningError",
)
