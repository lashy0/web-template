"""LoRaWAN DevEUI errors."""

from app.lib.exceptions import ApplicationClientError, ApplicationConflictError


class InvalidDevEuiError(ApplicationClientError):
    """A DevEUI is not exactly eight bytes encoded as hex (HTTP 400)."""

    code = "invalid_dev_eui"
    detail = "DevEUI must contain exactly 16 hexadecimal characters."


class InvalidDevEuiPrefixError(ApplicationClientError):
    """A DevEUI prefix is not exactly five bytes encoded as hex (HTTP 400)."""

    code = "invalid_dev_eui_prefix"
    detail = "DevEUI prefix must contain exactly 10 hexadecimal characters."


class DevEuiRangeOverflowError(ApplicationConflictError):
    """The prefix has no room left for the requested DevEUI range (HTTP 409)."""

    code = "dev_eui_range_overflow"
    detail = "The DevEUI prefix has no room for the requested quantity."


__all__ = (
    "DevEuiRangeOverflowError",
    "InvalidDevEuiError",
    "InvalidDevEuiPrefixError",
)
