from typing import Annotated

from pydantic import BeforeValidator

from app.components.keygen.dev_eui import normalize_dev_eui, normalize_dev_eui_prefix
from app.components.keygen.exceptions import InvalidDevEuiError, InvalidDevEuiPrefixError


def _normalize_dev_eui(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("DevEUI must be a string")
    try:
        return normalize_dev_eui(value.strip())
    except InvalidDevEuiError:
        raise ValueError("DevEUI must contain exactly 16 hex characters") from None


def _normalize_dev_eui_prefix(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("DevEUI prefix must be a string")
    try:
        return normalize_dev_eui_prefix(value.strip())
    except InvalidDevEuiPrefixError:
        raise ValueError("DevEUI prefix must contain exactly 10 hex characters") from None


DevEui = Annotated[str, BeforeValidator(_normalize_dev_eui)]
DevEuiPrefix = Annotated[str, BeforeValidator(_normalize_dev_eui_prefix)]
