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


__all__ = ("PakDeviceArchivedError", "PakDeviceCodeTakenError")
