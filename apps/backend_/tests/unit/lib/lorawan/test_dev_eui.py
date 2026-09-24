import pytest

from app.lib.lorawan import (
    DEV_EUI_SERIAL_MAX,
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
    derive_dev_eui_range,
    normalize_dev_eui,
    normalize_dev_eui_prefix,
)

pytestmark = pytest.mark.unit


def test_normalize_dev_eui_lowercases() -> None:
    assert normalize_dev_eui("0123456789ABCDEF") == "0123456789abcdef"


def test_normalize_dev_eui_rejects_non_hex_value() -> None:
    with pytest.raises(InvalidDevEuiError):
        normalize_dev_eui("0123456789abcdeg")


def test_normalize_dev_eui_prefix_lowercases() -> None:
    assert normalize_dev_eui_prefix("A1B2C3D4E5") == "a1b2c3d4e5"


def test_normalize_dev_eui_prefix_rejects_short_value() -> None:
    with pytest.raises(InvalidDevEuiPrefixError):
        normalize_dev_eui_prefix("a1b2c3d4")


def test_derive_dev_eui_range_starts_at_first_serial() -> None:
    dev_eui_range = derive_dev_eui_range("a1b2c3d4e5", 100, first_serial=2)

    assert dev_eui_range == ("a1b2c3d4e5000002", "a1b2c3d4e5000065")


def test_derive_dev_eui_range_may_end_at_last_serial() -> None:
    dev_eui_range = derive_dev_eui_range("a1b2c3d4e5", 1, first_serial=DEV_EUI_SERIAL_MAX)

    assert dev_eui_range == ("a1b2c3d4e5ffffff", "a1b2c3d4e5ffffff")


def test_derive_dev_eui_range_rejects_serial_overflow() -> None:
    with pytest.raises(DevEuiRangeOverflowError):
        derive_dev_eui_range("a1b2c3d4e5", 2, first_serial=DEV_EUI_SERIAL_MAX)
