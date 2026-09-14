"""Deprecated compatibility bridge; use :mod:`app.components.keygen`."""

from app.components.keygen import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    Credentials,
    CredentialsGenerationError,
    InvalidDevEuiError,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
    generate_credentials,
)

__all__ = [
    "Abp10Credentials",
    "Abp11Credentials",
    "ActivationType",
    "Credentials",
    "CredentialsGenerationError",
    "InvalidDevEuiError",
    "LoRaWanVersion",
    "Otaa10Credentials",
    "Otaa11Credentials",
    "generate_credentials",
]
