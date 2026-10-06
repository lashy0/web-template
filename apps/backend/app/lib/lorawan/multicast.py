"""Multicast group addresses and keys.

The derivation reproduces the legacy web-otk service: devices and network
servers in the field were configured with its session keys, so the output must
stay byte-for-byte identical. It swaps the derivation bytes of LoRaWAN TS005,
where ``0x01`` gives the McAppSKey: here ``0x01`` gives the McNwkSKey.
"""

from secrets import token_hex

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.lib.lorawan.schemas import MulticastSessionKeys

MULTICAST_GROUP_IDS = (0, 1)
"""The McGroupIDs a KG unit is provisioned with, one group each."""

_PADDING = b"\x00" * 11
_NWK_S_KEY_BYTE = b"\x01"
_APP_S_KEY_BYTE = b"\x02"


def generate_multicast_address() -> str:
    """A random four-byte McAddr in lowercase hex."""
    return token_hex(4)


def generate_multicast_key() -> str:
    """A random sixteen-byte McKey in lowercase hex."""
    return token_hex(16)


def derive_multicast_session_keys(mc_addr: str, mc_key: str) -> MulticastSessionKeys:
    """Derive the session keys of a multicast group from its McKey and McAddr."""
    key = bytes.fromhex(mc_key)
    # The address enters the block least significant byte first.
    address = bytes.fromhex(mc_addr)[::-1]

    return MulticastSessionKeys(
        mc_nwk_s_key=_encrypt_block(key, _NWK_S_KEY_BYTE + address + _PADDING).hex(),
        mc_app_s_key=_encrypt_block(key, _APP_S_KEY_BYTE + address + _PADDING).hex(),
    )


def _encrypt_block(key: bytes, block: bytes) -> bytes:
    # ECB over a single block is a key derivation step, not message encryption.
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()

    return encryptor.update(block) + encryptor.finalize()


__all__ = (
    "MULTICAST_GROUP_IDS",
    "derive_multicast_session_keys",
    "generate_multicast_address",
    "generate_multicast_key",
)
