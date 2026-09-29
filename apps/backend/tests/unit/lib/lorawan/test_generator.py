import pytest

from app.lib.lorawan import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    Credentials,
    InvalidDevEuiError,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
    generate_credentials,
)

pytestmark = pytest.mark.unit


# Captured from the legacy key-gen service and its aes128-abp/aes128-ota
# binaries. Devices in the field carry these keys, so they are the contract.
@pytest.mark.parametrize(
    ("activation_type", "lorawan_version", "expected"),
    [
        (
            ActivationType.ABP,
            LoRaWanVersion.V1_0,
            Abp10Credentials(
                dev_addr="89abcdef",
                app_s_key="3c8e93e8a40dfe7929c5a774e616f877",
                nwk_s_key="f827e0d772f0b6c7b7d1f5a6c98820d4",
                app_key="8d11148a2893bafafafbcff750a27848",
            ),
        ),
        (
            ActivationType.ABP,
            LoRaWanVersion.V1_1,
            Abp11Credentials(
                dev_addr="89abcdef",
                app_s_key="3c8e93e8a40dfe7929c5a774e616f877",
                f_nwk_s_int_key="f827e0d772f0b6c7b7d1f5a6c98820d4",
                s_nwk_s_int_key="f23e7283c9c39315834b5602c38e2664",
                nwk_s_enc_key="c33b4ea833b48e111fd0821692e0ea80",
                app_key="8d11148a2893bafafafbcff750a27848",
            ),
        ),
        (
            ActivationType.OTAA,
            LoRaWanVersion.V1_0,
            Otaa10Credentials(
                dev_addr="89abcdef",
                app_key="5feadae4a3a1a5e787c5da53b7a425da",
            ),
        ),
        (
            ActivationType.OTAA,
            LoRaWanVersion.V1_1,
            Otaa11Credentials(
                dev_addr="89abcdef",
                app_key="5feadae4a3a1a5e787c5da53b7a425da",
                nwk_key="a0b4766a61c39067c970d671988f0319",
            ),
        ),
    ],
    ids=["abp-1.0", "abp-1.1", "otaa-1.0", "otaa-1.1"],
)
def test_generate_credentials_matches_legacy_key_gen(
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
    expected: Credentials,
) -> None:
    credentials = generate_credentials("0123456789abcdef", activation_type, lorawan_version)

    assert credentials == expected


def test_generate_credentials_rejects_invalid_dev_eui() -> None:
    with pytest.raises(InvalidDevEuiError):
        generate_credentials("0123456789abcdeg", ActivationType.OTAA, LoRaWanVersion.V1_0)
