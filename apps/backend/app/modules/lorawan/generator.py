from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .dev_eui import normalize_dev_eui
from .domain import ActivationType, LoRaWanVersion
from .exceptions import CredentialsGenerationError
from .schemas import (
    Abp10Credentials,
    Abp11Credentials,
    Credentials,
    Otaa10Credentials,
    Otaa11Credentials,
)

_ZERO_BLOCK = b"\x00" * 16
_DEV_EUI_XOR_MASK = 0xDE


def generate_credentials(
    dev_eui: str,
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
) -> Credentials:
    normalized_dev_eui = normalize_dev_eui(dev_eui)
    dev_eui_bytes = bytes.fromhex(normalized_dev_eui)
    dev_addr = normalized_dev_eui[-8:]

    if activation_type is ActivationType.ABP:
        return _generate_abp_credentials(dev_addr, dev_eui_bytes, lorawan_version)

    if activation_type is ActivationType.OTAA:
        return _generate_otaa_credentials(dev_addr, dev_eui_bytes, lorawan_version)

    raise CredentialsGenerationError(
        f"Unsupported activation type: {activation_type!r}"
    )


def _generate_abp_credentials(
    dev_addr: str,
    dev_eui: bytes,
    lorawan_version: LoRaWanVersion,
) -> Abp10Credentials | Abp11Credentials:
    f_nwk_s_int_key, s_nwk_s_int_key, nwk_s_enc_key, app_key = _derive_abp_base_keys(dev_eui)
    app_s_key = _encrypt_zero_block(f_nwk_s_int_key).hex()

    if lorawan_version is LoRaWanVersion.V1_0:
        return Abp10Credentials(
            devAddr=dev_addr,
            appSKey=app_s_key,
            nwkSKey=f_nwk_s_int_key.hex(),
            appKey=app_key.hex(),
        )

    if lorawan_version is LoRaWanVersion.V1_1:
        return Abp11Credentials(
            devAddr=dev_addr,
            appSKey=app_s_key,
            fNwkSIntKey=f_nwk_s_int_key.hex(),
            sNwkSIntKey=s_nwk_s_int_key.hex(),
            nwkSEncKey=nwk_s_enc_key.hex(),
            appKey=app_key.hex(),
        )

    raise CredentialsGenerationError(
        f"Unsupported LoRaWAN version: {lorawan_version!r}"
    )


def _generate_otaa_credentials(
    dev_addr: str,
    dev_eui: bytes,
    lorawan_version: LoRaWanVersion,
) -> Otaa10Credentials | Otaa11Credentials:
    nwk_key, app_key = _derive_otaa_base_keys(dev_eui)

    if lorawan_version is LoRaWanVersion.V1_0:
        return Otaa10Credentials(devAddr=dev_addr, appKey=app_key.hex())

    if lorawan_version is LoRaWanVersion.V1_1:
        return Otaa11Credentials(
            devAddr=dev_addr,
            appKey=app_key.hex(),
            nwkKey=nwk_key.hex(),
        )

    raise CredentialsGenerationError(
        f"Unsupported LoRaWAN version: {lorawan_version!r}"
    )


def _derive_abp_base_keys(dev_eui: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    derivation_seed = _build_derivation_seed(dev_eui)
    f_nwk_s_int_key = _encrypt_zero_block(derivation_seed)
    s_nwk_s_int_key = _encrypt_zero_block(f_nwk_s_int_key[8:] + derivation_seed[8:])
    nwk_s_enc_key = _encrypt_zero_block(derivation_seed[:8] + f_nwk_s_int_key[:8])
    app_key = _encrypt_zero_block(f_nwk_s_int_key[:8] + nwk_s_enc_key[8:])

    return f_nwk_s_int_key, s_nwk_s_int_key, nwk_s_enc_key, app_key


def _derive_otaa_base_keys(dev_eui: bytes) -> tuple[bytes, bytes]:
    derivation_seed = _build_derivation_seed(dev_eui)
    nwk_key = _encrypt_zero_block(
        derivation_seed[4:8] + derivation_seed[:8] + derivation_seed[:4]
    )
    app_key = _encrypt_zero_block(nwk_key[:8] + derivation_seed[:8])

    return nwk_key, app_key


def _build_derivation_seed(dev_eui: bytes) -> bytes:
    return bytes(byte ^ _DEV_EUI_XOR_MASK for byte in dev_eui * 2)


def _encrypt_zero_block(key: bytes) -> bytes:
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()

    return encryptor.update(_ZERO_BLOCK) + encryptor.finalize()
