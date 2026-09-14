import pytest

from app.components.keygen.dev_eui import (
    derive_dev_eui_range,
    normalize_dev_eui,
    normalize_dev_eui_prefix,
)
from app.components.keygen.exceptions import (
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
)


@pytest.mark.unit
def test_dev_eui_and_prefix_are_canonicalized_to_lowercase() -> None:
    assert normalize_dev_eui("0123456789ABCDEF") == "0123456789abcdef"
    assert normalize_dev_eui_prefix("A1B2C3D4E5") == "a1b2c3d4e5"


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    ["", "0123456789abcde", "0123456789abcdef0", "0123456789abcdeg", " 0123456789abcdef"],
)
def test_invalid_dev_eui_is_rejected_without_trimming(value: str) -> None:
    with pytest.raises(InvalidDevEuiError, match="16 hexadecimal"):
        normalize_dev_eui(value)


@pytest.mark.unit
@pytest.mark.parametrize("value", ["", "a1b2c3d4", "a1b2c3d4e50", "a1b2c3d4ez"])
def test_invalid_dev_eui_prefix_is_rejected(value: str) -> None:
    with pytest.raises(InvalidDevEuiPrefixError, match="10 hexadecimal"):
        normalize_dev_eui_prefix(value)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("maximum_dev_eui", "quantity", "expected"),
    [
        (None, 1, ("a1b2c3d4e5000001", "a1b2c3d4e5000001")),
        ("a1b2c3d4e5000001", 100, ("a1b2c3d4e5000002", "a1b2c3d4e5000065")),
        ("a1b2c3d4e5fffffe", 1, ("a1b2c3d4e5ffffff", "a1b2c3d4e5ffffff")),
    ],
)
def test_dev_eui_range_derivation_preserves_existing_suffix_boundaries(
    maximum_dev_eui: str | None,
    quantity: int,
    expected: tuple[str, str],
) -> None:
    assert derive_dev_eui_range("A1B2C3D4E5", quantity, maximum_dev_eui=maximum_dev_eui) == expected


@pytest.mark.unit
def test_dev_eui_range_derivation_rejects_suffix_overflow() -> None:
    with pytest.raises(DevEuiRangeOverflowError):
        derive_dev_eui_range("a1b2c3d4e5", 1, maximum_dev_eui="a1b2c3d4e5ffffff")
