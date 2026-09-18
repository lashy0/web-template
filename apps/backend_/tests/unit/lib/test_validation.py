from __future__ import annotations

import pytest

from app.lib.validation import (
    PasswordValidationError,
    ValidationError,
    get_password_strength,
    validate_login,
    validate_name,
    validate_password,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  Ada   Lovelace  ", "Ada Lovelace"),
        ("Мария-Антуанетта", "Мария-Антуанетта"),
        ("O'Connor", "O'Connor"),
    ],
)
def test_validate_name_normalizes_valid_names(value: str, expected: str) -> None:
    assert validate_name(value) == expected


@pytest.mark.unit
@pytest.mark.parametrize("value", ["", "   ", "Ada123", "!!!!!", "aaaaa"])
def test_validate_name_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_name(value)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  Operator_01  ", "operator_01"),
        ("user.name-2", "user.name-2"),
    ],
)
def test_validate_login_normalizes_valid_logins(value: str, expected: str) -> None:
    assert validate_login(value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    ["ab", "system", "admin!", "-operator", "aaaa", "a" * 65],
)
def test_validate_login_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_login(value)


@pytest.mark.unit
def test_validate_password_accepts_a_strong_password() -> None:
    password = "ValidPassword_2026!"

    assert validate_password(password) == password


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "short1!A",
        "onlylowercase123!",
        "ONLYUPPERCASE123!",
        "NoDigitsHere!!!",
        "NoSpecialCharacter12",
        "aaaaaaaaaaaa",
        "123Abcdefghij!",
    ],
)
def test_validate_password_rejects_weak_passwords(value: str) -> None:
    with pytest.raises(PasswordValidationError):
        validate_password(value)


@pytest.mark.unit
def test_password_strength_reports_requirements_and_feedback() -> None:
    analysis = get_password_strength("lowercase")

    assert analysis["strength"] == "weak"
    assert analysis["requirements"]["uppercase"] is False
    assert "Include uppercase letters" in analysis["feedback"]


@pytest.mark.unit
def test_password_strength_reports_strong_password() -> None:
    analysis = get_password_strength("VeryStrongPassword_2026!")

    assert analysis["strength"] == "strong"
    assert analysis["score"] >= 7
