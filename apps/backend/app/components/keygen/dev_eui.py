"""Canonical DevEUI parsing, normalization, and pure range derivation."""

import re

from .exceptions import (
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
)

_DEV_EUI_PATTERN = re.compile(r"[0-9a-fA-F]{16}")
_DEV_EUI_PREFIX_PATTERN = re.compile(r"[0-9a-fA-F]{10}")
_DEV_EUI_SUFFIX_MAX = 0xFFFFFF


def normalize_dev_eui(dev_eui: str) -> str:
    """Return the canonical lowercase representation of an eight-byte DevEUI."""
    if not isinstance(dev_eui, str) or _DEV_EUI_PATTERN.fullmatch(dev_eui) is None:
        raise InvalidDevEuiError("DevEUI must contain exactly 16 hexadecimal characters")

    return dev_eui.lower()


def normalize_dev_eui_prefix(prefix: str) -> str:
    """Return the canonical lowercase representation of a five-byte DevEUI prefix."""
    if not isinstance(prefix, str) or _DEV_EUI_PREFIX_PATTERN.fullmatch(prefix) is None:
        raise InvalidDevEuiPrefixError(
            "DevEUI prefix must contain exactly 10 hexadecimal characters"
        )

    return prefix.lower()


def derive_dev_eui_range(
    prefix: str,
    quantity: int,
    *,
    maximum_dev_eui: str | None = None,
) -> tuple[str, str]:
    """Derive the first and last DevEUI for the next contiguous allocation.

    Prefix selection, locking, and storage lookup intentionally remain outside this
    component; callers supply the persisted maximum value when one exists.
    """
    normalized_prefix = normalize_dev_eui_prefix(prefix)
    start = int(maximum_dev_eui[-6:], 16) + 1 if maximum_dev_eui else 1
    end = start + quantity - 1
    if end > _DEV_EUI_SUFFIX_MAX:
        raise DevEuiRangeOverflowError

    return f"{normalized_prefix}{start:06x}", f"{normalized_prefix}{end:06x}"
