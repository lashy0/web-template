import pytest

from app.lib import validation

pytestmark = pytest.mark.unit


def test_validate_not_empty_strips_whitespace() -> None:
    assert validation.validate_not_empty("  test  ") == "test"


def test_validate_not_empty_rejects_blank() -> None:
    with pytest.raises(validation.ValidationError):
        validation.validate_not_empty("   ")


def test_validate_length_accepts_value_within_bounds() -> None:
    assert validation.validate_length("abc", min_length=2, max_length=5) == "abc"


@pytest.mark.parametrize(
    ("min_length", "max_length"),
    [
        (5, None),
        (0, 2),
    ],
    ids=["too-short", "too-long"],
)
def test_validate_length_rejects_value_out_of_bounds(min_length: int, max_length: int | None) -> None:
    with pytest.raises(validation.ValidationError):
        validation.validate_length("abc", min_length=min_length, max_length=max_length)


def test_validate_name_collapses_whitespace() -> None:
    assert validation.validate_name("  Ada   Lovelace  ") == "Ada Lovelace"


@pytest.mark.parametrize(
    "name",
    [
        "   ",
        "A" * (validation.NAME_MAX_LENGTH + 1),
    ],
    ids=["blank", "too-long"],
)
def test_validate_name_rejects_wrong_length(name: str) -> None:
    with pytest.raises(validation.ValidationError):
        validation.validate_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "Ada123",
        "Adaaaaa",
    ],
    ids=["digits", "repeated-characters"],
)
def test_validate_name_rejects_suspicious_text(name: str) -> None:
    with pytest.raises(validation.ValidationError):
        validation.validate_name(name)


def test_validate_login_normalizes_case_and_whitespace() -> None:
    assert validation.validate_login("  Operator_01  ") == "operator_01"


@pytest.mark.parametrize(
    "login",
    [
        "ab",
        "a" * (validation.LOGIN_MAX_LENGTH + 1),
    ],
    ids=["too-short", "too-long"],
)
def test_validate_login_rejects_wrong_length(login: str) -> None:
    with pytest.raises(validation.ValidationError):
        validation.validate_login(login)


@pytest.mark.parametrize(
    "login",
    [
        "admin!",
        "system",
        "operaaaator",
    ],
    ids=["invalid-characters", "reserved", "repeated-characters"],
)
def test_validate_login_rejects_unusable_login(login: str) -> None:
    with pytest.raises(validation.ValidationError):
        validation.validate_login(login)


def test_validate_password_accepts_strong_password() -> None:
    assert validation.validate_password("ValidPassword_2026!") == "ValidPassword_2026!"


@pytest.mark.parametrize(
    "password",
    [
        "Short_1!",
        "Long_1!" + "a" * validation.PASSWORD_MAX_LENGTH,
    ],
    ids=["too-short", "too-long"],
)
def test_validate_password_rejects_wrong_length(password: str) -> None:
    with pytest.raises(validation.PasswordValidationError):
        validation.validate_password(password)


@pytest.mark.parametrize(
    "password",
    [
        "validpassword_2026!",
        "VALIDPASSWORD_2026!",
        "ValidPassword_nodigit!",
        "ValidPassword2026",
    ],
    ids=["no-uppercase", "no-lowercase", "no-digit", "no-special"],
)
def test_validate_password_requires_each_character_class(password: str) -> None:
    with pytest.raises(validation.PasswordValidationError):
        validation.validate_password(password)


@pytest.mark.parametrize(
    "password",
    [
        "Abc_Password_2026!",
        "Qwerty_Password_2026!",
    ],
    ids=["sequence", "keyboard-row"],
)
def test_validate_password_rejects_predictable_start(password: str) -> None:
    with pytest.raises(validation.PasswordValidationError):
        validation.validate_password(password)
