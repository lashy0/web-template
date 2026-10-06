import pytest

from app.lib.lorawan import (
    MulticastSessionKeys,
    derive_multicast_session_keys,
    generate_multicast_address,
    generate_multicast_key,
)

pytestmark = pytest.mark.unit


# Groups configured by the legacy web-otk service; devices and network servers
# carry these session keys, so they are the contract.
@pytest.mark.parametrize(
    ("mc_addr", "mc_key", "expected"),
    [
        (
            "5ef184c9",
            "43b650d61d8f9970df9b163ab6621b96",
            MulticastSessionKeys(
                mc_nwk_s_key="6278651bc1c79abe26356d0f91065c37",
                mc_app_s_key="78e07423ffdd796b6057392e0a8278a1",
            ),
        ),
        (
            "a48ee26b",
            "2d2ffbc2f01780ec1ffdb258cd295a41",
            MulticastSessionKeys(
                mc_nwk_s_key="8dad3df93803fc60098013bf906091cb",
                mc_app_s_key="e031ae11d29fa183a6e5755854f37b2d",
            ),
        ),
    ],
)
def test_derive_multicast_session_keys_matches_legacy_groups(
    mc_addr: str,
    mc_key: str,
    expected: MulticastSessionKeys,
) -> None:
    assert derive_multicast_session_keys(mc_addr, mc_key) == expected


def test_generate_multicast_address_returns_four_bytes_of_lowercase_hex() -> None:
    address = generate_multicast_address()

    assert (len(address), address == address.lower(), len(bytes.fromhex(address))) == (8, True, 4)


def test_generate_multicast_key_returns_sixteen_bytes_of_lowercase_hex() -> None:
    key = generate_multicast_key()

    assert (len(key), key == key.lower(), len(bytes.fromhex(key))) == (32, True, 16)
