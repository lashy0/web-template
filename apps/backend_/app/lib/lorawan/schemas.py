"""LoRaWAN configuration values and typed credential payloads."""

from enum import StrEnum

import msgspec


class ActivationType(StrEnum):
    OTAA = "otaa"
    ABP = "abp"


class LoRaWanVersion(StrEnum):
    V1_0 = "1.0"
    V1_1 = "1.1"


class CredentialsPayload(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    """Base of the credential payloads; field names are part of the API contract."""


class Abp10Credentials(CredentialsPayload, frozen=True):
    dev_addr: str
    app_s_key: str
    nwk_s_key: str
    app_key: str


class Abp11Credentials(CredentialsPayload, frozen=True):
    dev_addr: str
    app_s_key: str
    f_nwk_s_int_key: str
    s_nwk_s_int_key: str
    nwk_s_enc_key: str
    app_key: str


class Otaa10Credentials(CredentialsPayload, frozen=True):
    dev_addr: str
    app_key: str


class Otaa11Credentials(CredentialsPayload, frozen=True):
    dev_addr: str
    app_key: str
    nwk_key: str


type Credentials = Abp10Credentials | Abp11Credentials | Otaa10Credentials | Otaa11Credentials


__all__ = (
    "Abp10Credentials",
    "Abp11Credentials",
    "ActivationType",
    "Credentials",
    "CredentialsPayload",
    "LoRaWanVersion",
    "Otaa10Credentials",
    "Otaa11Credentials",
)
