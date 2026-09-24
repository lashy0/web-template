"""Canonical DevEUI parsing, normalization and range derivation."""

import re

from app.lib.lorawan.exceptions import (
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
)

_DEV_EUI_PATTERN = re.compile(r"[0-9a-fA-F]{16}")
_DEV_EUI_PREFIX_PATTERN = re.compile(r"[0-9a-fA-F]{10}")
DEV_EUI_SERIAL_MAX = 0xFFFFFF
"""The last serial, the six-hex-digit DevEUI suffix, available under one prefix."""


def normalize_dev_eui(dev_eui: str) -> str:
    """Return the canonical lowercase representation of an eight-byte DevEUI."""
    if _DEV_EUI_PATTERN.fullmatch(dev_eui) is None:
        raise InvalidDevEuiError

    return dev_eui.lower()


def normalize_dev_eui_prefix(prefix: str) -> str:
    """Return the canonical lowercase representation of a five-byte DevEUI prefix."""
    if _DEV_EUI_PREFIX_PATTERN.fullmatch(prefix) is None:
        raise InvalidDevEuiPrefixError

    return prefix.lower()


def derive_dev_eui_range(prefix: str, quantity: int, *, first_serial: int = 1) -> tuple[str, str]:
    """Return the first and last DevEUI of ``quantity`` serials starting at ``first_serial``.

    The serial is the six-hex-digit suffix after the prefix. Allocating serials
    and locking the prefix stay with the caller.

    Raises:
        DevEuiRangeOverflowError: The range would exceed the six-hex-digit suffix.
    """
    normalized_prefix = normalize_dev_eui_prefix(prefix)
    last_serial = first_serial + quantity - 1

    if last_serial > DEV_EUI_SERIAL_MAX:
        raise DevEuiRangeOverflowError

    return f"{normalized_prefix}{first_serial:06x}", f"{normalized_prefix}{last_serial:06x}"


__all__ = ("DEV_EUI_SERIAL_MAX", "derive_dev_eui_range", "normalize_dev_eui", "normalize_dev_eui_prefix")
