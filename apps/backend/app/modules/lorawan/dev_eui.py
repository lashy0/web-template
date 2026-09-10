import re

from .exceptions import InvalidDevEuiError

_DEV_EUI_PATTERN = re.compile(r"[0-9a-fA-F]{16}")


def normalize_dev_eui(dev_eui: str) -> str:
    """Return the canonical lowercase representation of an eight-byte DevEUI."""
    if not isinstance(dev_eui, str) or _DEV_EUI_PATTERN.fullmatch(dev_eui) is None:
        raise InvalidDevEuiError("DevEUI must contain exactly 16 hexadecimal characters")

    return dev_eui.lower()
