"""Canonical DevEUI parsing, normalization and range derivation."""

import re

from app.lib.lorawan.exceptions import (
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
)

_DEV_EUI_PATTERN = re.compile(r"[0-9a-fA-F]{16}")
_DEV_EUI_PREFIX_PATTERN = re.compile(r"[0-9a-fA-F]{10}")
_DEV_EUI_SUFFIX_MAX = 0xFFFFFF


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


def derive_dev_eui_range(
    prefix: str,
    quantity: int,
    *,
    maximum_dev_eui: str | None = None,
) -> tuple[str, str]:
    """Derive the first and last DevEUI of the next contiguous allocation.

    Locking and the lookup of the allocated maximum stay with the caller, which
    supplies ``maximum_dev_eui`` when the prefix already has allocations.

    Raises:
        DevEuiRangeOverflowError: The range would exceed the six-hex-digit suffix.
    """
    normalized_prefix = normalize_dev_eui_prefix(prefix)
    start = int(maximum_dev_eui[-6:], 16) + 1 if maximum_dev_eui else 1
    end = start + quantity - 1

    if end > _DEV_EUI_SUFFIX_MAX:
        raise DevEuiRangeOverflowError

    return f"{normalized_prefix}{start:06x}", f"{normalized_prefix}{end:06x}"


__all__ = ("derive_dev_eui_range", "normalize_dev_eui", "normalize_dev_eui_prefix")
