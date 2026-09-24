import pytest

from app.lib import validation

pytestmark = pytest.mark.unit


def test_validate_not_empty() -> None:
    assert validation.validate_not_empty("  test  ") == "test"

    with pytest.raises(validation.ValidationError):
        validation.validate_not_empty("   ")


def test_validate_length() -> None:
    assert validation.validate_length("abc", min_length=2, max_length=5) == "abc"

    with pytest.raises(validation.ValidationError):
        validation.validate_length("abc", min_length=5)

    with pytest.raises(validation.ValidationError):
        validation.validate_length("abc", max_length=2)


def test_validate_name() -> None:
    assert validation.validate_name("  Ada   Lovelace  ") == "Ada Lovelace"

    with pytest.raises(validation.ValidationError):
        validation.validate_name("Ada123")


def test_validate_login() -> None:
    assert validation.validate_login("  Operator_01  ") == "operator_01"

    with pytest.raises(validation.ValidationError):
        validation.validate_login("admin!")


def test_validate_password() -> None:
    assert validation.validate_password("ValidPassword_2026!") == "ValidPassword_2026!"

    with pytest.raises(validation.PasswordValidationError):
        validation.validate_password("short1!A")
