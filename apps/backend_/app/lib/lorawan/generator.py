"""Deterministic LoRaWAN credential generation.

The derivation reproduces the legacy ``aes128-abp``/``aes128-ota`` key-gen
binaries: devices already in the field were provisioned with these keys, so the
output must stay byte-for-byte identical.
"""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.lib.lorawan.dev_eui import normalize_dev_eui
from app.lib.lorawan.schemas import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    Credentials,
    LoRaWanVersion,
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
    """Derive the credentials of one device from its DevEUI."""
    normalized_dev_eui = normalize_dev_eui(dev_eui)
    dev_eui_bytes = bytes.fromhex(normalized_dev_eui)
    dev_addr = normalized_dev_eui[-8:]

    match activation_type:
        case ActivationType.ABP:
            return _generate_abp_credentials(dev_addr, dev_eui_bytes, lorawan_version)
        case ActivationType.OTAA:
            return _generate_otaa_credentials(dev_addr, dev_eui_bytes, lorawan_version)


def _generate_abp_credentials(
    dev_addr: str,
    dev_eui: bytes,
    lorawan_version: LoRaWanVersion,
) -> Abp10Credentials | Abp11Credentials:
    f_nwk_s_int_key, s_nwk_s_int_key, nwk_s_enc_key, app_key = _derive_abp_base_keys(dev_eui)
    app_s_key = _encrypt_zero_block(f_nwk_s_int_key).hex()

    match lorawan_version:
        case LoRaWanVersion.V1_0:
            return Abp10Credentials(
                dev_addr=dev_addr,
                app_s_key=app_s_key,
                nwk_s_key=f_nwk_s_int_key.hex(),
                app_key=app_key.hex(),
            )
        case LoRaWanVersion.V1_1:
            return Abp11Credentials(
                dev_addr=dev_addr,
                app_s_key=app_s_key,
                f_nwk_s_int_key=f_nwk_s_int_key.hex(),
                s_nwk_s_int_key=s_nwk_s_int_key.hex(),
                nwk_s_enc_key=nwk_s_enc_key.hex(),
                app_key=app_key.hex(),
            )


def _generate_otaa_credentials(
    dev_addr: str,
    dev_eui: bytes,
    lorawan_version: LoRaWanVersion,
) -> Otaa10Credentials | Otaa11Credentials:
    nwk_key, app_key = _derive_otaa_base_keys(dev_eui)

    match lorawan_version:
        case LoRaWanVersion.V1_0:
            return Otaa10Credentials(
                dev_addr=dev_addr,
                app_key=app_key.hex(),
            )
        case LoRaWanVersion.V1_1:
            return Otaa11Credentials(
                dev_addr=dev_addr,
                app_key=app_key.hex(),
                nwk_key=nwk_key.hex(),
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
    nwk_key = _encrypt_zero_block(derivation_seed[4:8] + derivation_seed[:8] + derivation_seed[:4])
    app_key = _encrypt_zero_block(nwk_key[:8] + derivation_seed[:8])

    return nwk_key, app_key


def _build_derivation_seed(dev_eui: bytes) -> bytes:
    return bytes(byte ^ _DEV_EUI_XOR_MASK for byte in dev_eui * 2)


def _encrypt_zero_block(key: bytes) -> bytes:
    # ECB over a single zero block is a key derivation step, not message encryption.
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()

    return encryptor.update(_ZERO_BLOCK) + encryptor.finalize()


__all__ = ("generate_credentials",)
