from typing import cast

import pytest

from app.core.exceptions import AppError, InvalidInputError
from app.modules.lorawan import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    InvalidDevEuiError,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
    generate_credentials,
)

# These literal fixtures were captured from the legacy key-gen response builder
# and its aes128-abp/aes128-ota binaries before this Python port existed. They
# intentionally do not invoke this module or share any algorithm helpers.
GOLDEN_CASES = (
    (
        "be109d2ba809478a",
        ActivationType.ABP,
        LoRaWanVersion.V1_0,
        Abp10Credentials,
        {
            "dev_addr": "a809478a",
            "app_s_key": "6b7f8f492d366b2f613692c7b14509f5",
            "nwk_s_key": "7a9285f358449bca1e11b976111433d7",
            "app_key": "453ed10bbc40b3c58a0346288ad71415",
        },
    ),
    (
        "be109d2ba809478a",
        ActivationType.ABP,
        LoRaWanVersion.V1_1,
        Abp11Credentials,
        {
            "dev_addr": "a809478a",
            "app_s_key": "6b7f8f492d366b2f613692c7b14509f5",
            "f_nwk_s_int_key": "7a9285f358449bca1e11b976111433d7",
            "s_nwk_s_int_key": "fe05fb8d309214e20373436365026ec2",
            "nwk_s_enc_key": "fe3f403957ca2640b5a66e1f400df2fa",
            "app_key": "453ed10bbc40b3c58a0346288ad71415",
        },
    ),
    (
        "be109d2ba809478a",
        ActivationType.OTAA,
        LoRaWanVersion.V1_0,
        Otaa10Credentials,
        {"dev_addr": "a809478a", "app_key": "c5251b61cb2c78b4325fa7933a0181b6"},
    ),
    (
        "be109d2ba809478a",
        ActivationType.OTAA,
        LoRaWanVersion.V1_1,
        Otaa11Credentials,
        {
            "dev_addr": "a809478a",
            "app_key": "c5251b61cb2c78b4325fa7933a0181b6",
            "nwk_key": "7b2b92c1fe1d348882b0b0db100ca2c3",
        },
    ),
    (
        "0016c00000000001",
        ActivationType.ABP,
        LoRaWanVersion.V1_0,
        Abp10Credentials,
        {
            "dev_addr": "00000001",
            "app_s_key": "2fb91fc46413bb1240117469910022e5",
            "nwk_s_key": "4bfb3784e7970fd79eeba60fc026c0f4",
            "app_key": "9f7310bfaea67606bc66a5238cf76080",
        },
    ),
    (
        "0016c00000000001",
        ActivationType.ABP,
        LoRaWanVersion.V1_1,
        Abp11Credentials,
        {
            "dev_addr": "00000001",
            "app_s_key": "2fb91fc46413bb1240117469910022e5",
            "f_nwk_s_int_key": "4bfb3784e7970fd79eeba60fc026c0f4",
            "s_nwk_s_int_key": "7b50ba57dccecbb533e77063dbb15a36",
            "nwk_s_enc_key": "533861e03b1616f14c5be36a8a26bb6c",
            "app_key": "9f7310bfaea67606bc66a5238cf76080",
        },
    ),
    (
        "0016c00000000001",
        ActivationType.OTAA,
        LoRaWanVersion.V1_0,
        Otaa10Credentials,
        {"dev_addr": "00000001", "app_key": "b0e2cf1fd1cbf922f28aa40e60ba4070"},
    ),
    (
        "0016c00000000001",
        ActivationType.OTAA,
        LoRaWanVersion.V1_1,
        Otaa11Credentials,
        {
            "dev_addr": "00000001",
            "app_key": "b0e2cf1fd1cbf922f28aa40e60ba4070",
            "nwk_key": "41843230e73753691799e87497fd709a",
        },
    ),
    (
        "0000000000000001",
        ActivationType.ABP,
        LoRaWanVersion.V1_0,
        Abp10Credentials,
        {
            "dev_addr": "00000001",
            "app_s_key": "39aac711bfd1c4a1ffe48fd3f727851f",
            "nwk_s_key": "4aa0eb90440970eaf8e1b2267bfcf0d6",
            "app_key": "557c1950ed4b2b1afd386ec27f179d80",
        },
    ),
    (
        "0000000000000001",
        ActivationType.ABP,
        LoRaWanVersion.V1_1,
        Abp11Credentials,
        {
            "dev_addr": "00000001",
            "app_s_key": "39aac711bfd1c4a1ffe48fd3f727851f",
            "f_nwk_s_int_key": "4aa0eb90440970eaf8e1b2267bfcf0d6",
            "s_nwk_s_int_key": "acc0a4d4627ace128fdf43fe26f9847a",
            "nwk_s_enc_key": "bd6383dd2faf7a2b20c2ccb861c11d79",
            "app_key": "557c1950ed4b2b1afd386ec27f179d80",
        },
    ),
    (
        "0000000000000001",
        ActivationType.OTAA,
        LoRaWanVersion.V1_0,
        Otaa10Credentials,
        {"dev_addr": "00000001", "app_key": "504d25b1d037e13880db81ddfda330f8"},
    ),
    (
        "0000000000000001",
        ActivationType.OTAA,
        LoRaWanVersion.V1_1,
        Otaa11Credentials,
        {
            "dev_addr": "00000001",
            "app_key": "504d25b1d037e13880db81ddfda330f8",
            "nwk_key": "c8988d5701824799d27403ebfed4bf9a",
        },
    ),
    (
        "0123456789abcdef",
        ActivationType.ABP,
        LoRaWanVersion.V1_0,
        Abp10Credentials,
        {
            "dev_addr": "89abcdef",
            "app_s_key": "3c8e93e8a40dfe7929c5a774e616f877",
            "nwk_s_key": "f827e0d772f0b6c7b7d1f5a6c98820d4",
            "app_key": "8d11148a2893bafafafbcff750a27848",
        },
    ),
    (
        "0123456789abcdef",
        ActivationType.ABP,
        LoRaWanVersion.V1_1,
        Abp11Credentials,
        {
            "dev_addr": "89abcdef",
            "app_s_key": "3c8e93e8a40dfe7929c5a774e616f877",
            "f_nwk_s_int_key": "f827e0d772f0b6c7b7d1f5a6c98820d4",
            "s_nwk_s_int_key": "f23e7283c9c39315834b5602c38e2664",
            "nwk_s_enc_key": "c33b4ea833b48e111fd0821692e0ea80",
            "app_key": "8d11148a2893bafafafbcff750a27848",
        },
    ),
    (
        "0123456789abcdef",
        ActivationType.OTAA,
        LoRaWanVersion.V1_0,
        Otaa10Credentials,
        {"dev_addr": "89abcdef", "app_key": "5feadae4a3a1a5e787c5da53b7a425da"},
    ),
    (
        "0123456789abcdef",
        ActivationType.OTAA,
        LoRaWanVersion.V1_1,
        Otaa11Credentials,
        {
            "dev_addr": "89abcdef",
            "app_key": "5feadae4a3a1a5e787c5da53b7a425da",
            "nwk_key": "a0b4766a61c39067c970d671988f0319",
        },
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("dev_eui", "activation_type", "lorawan_version", "expected_type", "expected"),
    GOLDEN_CASES,
)
def test_generate_credentials_matches_legacy_golden_payload(
    dev_eui: str,
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
    expected_type: type[
        Abp10Credentials | Abp11Credentials | Otaa10Credentials | Otaa11Credentials
    ],
    expected: dict[str, str],
) -> None:
    credentials = generate_credentials(dev_eui, activation_type, lorawan_version)

    assert isinstance(credentials, expected_type)
    assert credentials.model_dump() == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("activation_type", "lorawan_version"),
    [
        (ActivationType.ABP, LoRaWanVersion.V1_0),
        (ActivationType.ABP, LoRaWanVersion.V1_1),
        (ActivationType.OTAA, LoRaWanVersion.V1_0),
        (ActivationType.OTAA, LoRaWanVersion.V1_1),
    ],
)
def test_dev_eui_is_case_insensitive(
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
) -> None:
    lowercase = generate_credentials("0123456789abcdef", activation_type, lorawan_version)
    uppercase = generate_credentials("0123456789ABCDEF", activation_type, lorawan_version)

    assert uppercase == lowercase


@pytest.mark.unit
@pytest.mark.parametrize(
    "dev_eui",
    ["", "0123456789abcde", "0123456789abcdef0", "0123456789abcdeg", " 0123456789abcdef"],
)
def test_invalid_dev_eui_raises_domain_error(dev_eui: str) -> None:
    with pytest.raises(InvalidDevEuiError, match="16 hexadecimal"):
        generate_credentials(dev_eui, ActivationType.OTAA, LoRaWanVersion.V1_0)


@pytest.mark.unit
def test_non_string_dev_eui_raises_domain_error() -> None:
    with pytest.raises(InvalidDevEuiError, match="16 hexadecimal"):
        generate_credentials(cast(str, 123), ActivationType.OTAA, LoRaWanVersion.V1_0)


@pytest.mark.unit
def test_invalid_dev_eui_error_uses_the_backend_domain_error_hierarchy() -> None:
    error = InvalidDevEuiError()

    assert isinstance(error, AppError)
    assert isinstance(error, InvalidInputError)
