import re
from typing import Annotated

from pydantic import BeforeValidator

DEV_EUI_PATTERN = re.compile(r"^[0-9a-f]{16}$")
DEV_EUI_PREFIX_PATTERN = re.compile(r"^[0-9a-f]{10}$")


def normalize_dev_eui(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("DevEUI must be a string")

    value = value.strip().lower()
    if not DEV_EUI_PATTERN.fullmatch(value):
        raise ValueError("DevEUI must contain exactly 16 hex characters")

    return value


def normalize_dev_eui_prefix(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("DevEUI prefix must be a string")

    value = value.strip().lower()
    if not DEV_EUI_PREFIX_PATTERN.fullmatch(value):
        raise ValueError("DevEUI prefix must contain exactly 10 hex characters")

    return value


DevEui = Annotated[str, BeforeValidator(normalize_dev_eui)]
DevEuiPrefix = Annotated[str, BeforeValidator(normalize_dev_eui_prefix)]
