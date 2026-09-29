"""LoRaWAN DevEUI allocation and credential derivation.

Pure functions without database or configuration access; the production domain
supplies locks and persistence.
"""

from app.lib.lorawan.dev_eui import (
    DEV_EUI_SERIAL_MAX,
    derive_dev_eui_range,
    normalize_dev_eui,
    normalize_dev_eui_prefix,
)
from app.lib.lorawan.exceptions import (
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
)
from app.lib.lorawan.generator import generate_credentials
from app.lib.lorawan.schemas import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    Credentials,
    CredentialsPayload,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
)

__all__ = (
    "DEV_EUI_SERIAL_MAX",
    "Abp10Credentials",
    "Abp11Credentials",
    "ActivationType",
    "Credentials",
    "CredentialsPayload",
    "DevEuiRangeOverflowError",
    "InvalidDevEuiError",
    "InvalidDevEuiPrefixError",
    "LoRaWanVersion",
    "Otaa10Credentials",
    "Otaa11Credentials",
    "derive_dev_eui_range",
    "generate_credentials",
    "normalize_dev_eui",
    "normalize_dev_eui_prefix",
)
