"""Field validators shared by request schemas.

A field type such as ``Login`` carries the constraints that fit in the OpenAPI
schema, so the frontend generates the same rules for its forms; msgspec checks
them when it decodes a request. The ``validate_*`` functions normalize the
value and apply the remaining rules; they also run for structs built in code,
which msgspec does not check.
"""

import re
import secrets
import string
from typing import Annotated

import msgspec

from app.lib.exceptions import ApplicationClientError

NAME_ALLOWED = r"^[a-zA-ZÀ-ÿĀ-žА-яЁё\s'.-]+$"
NAME_WHITESPACE_PATTERN = re.compile(r"\s+")
NAME_VALID_PATTERN = re.compile(NAME_ALLOWED)
NAME_REPEATED_PATTERN = re.compile(r"(.)\1{4,}")

LOGIN_VALID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
LOGIN_REPEATED_PATTERN = re.compile(r"(.)\1{3,}")

_PASSWORD_SPECIAL_CLASS = r"""[!@#$%^&*(),.?":{}|<>_+=\-\[\]\\/~`]"""
_PASSWORD_PREDICTABLE_STARTS = (
    "012",
    "123",
    "234",
    "345",
    "456",
    "567",
    "678",
    "789",
    "890",
    "abc",
    "bcd",
    "cde",
    "qwe",
    "asd",
    "zxc",
)
PASSWORD_UPPERCASE_PATTERN = re.compile(r"[A-Z]")
PASSWORD_LOWERCASE_PATTERN = re.compile(r"[a-z]")
PASSWORD_DIGIT_PATTERN = re.compile(r"\d")
PASSWORD_SPECIAL_PATTERN = re.compile(_PASSWORD_SPECIAL_CLASS)
# A password that passes the character-class checks can still start with a
# run a person types without thinking.
PASSWORD_PREDICTABLE_START_PATTERN = re.compile(
    f"^({'|'.join(_PASSWORD_PREDICTABLE_STARTS)})",
    re.IGNORECASE,
)


def _any_case(text: str) -> str:
    """Spell out case-insensitivity, for which JavaScript patterns have no inline flag."""
    return "".join(f"[{char.upper()}{char.lower()}]" if char.isalpha() else char for char in text)


PASSWORD_ALLOWED = (
    f"^(?!{'|'.join(_any_case(start) for start in _PASSWORD_PREDICTABLE_STARTS)})"
    rf"(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*{_PASSWORD_SPECIAL_CLASS})"
)
"""Every password rule above, as one pattern for the OpenAPI schema."""


NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 128

LOGIN_MIN_LENGTH = 3
LOGIN_MAX_LENGTH = 64

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128

PersonName = Annotated[
    str,
    msgspec.Meta(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH, pattern=NAME_ALLOWED),
]
Login = Annotated[
    str,
    # Upper case is accepted; ``validate_login`` lowers it.
    msgspec.Meta(
        min_length=LOGIN_MIN_LENGTH,
        max_length=LOGIN_MAX_LENGTH,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$",
    ),
]
Password = Annotated[
    str,
    msgspec.Meta(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH, pattern=PASSWORD_ALLOWED),
]


# `admin`, `administrator`, etc. intentionally are NOT reserved:
# they are valid application logins for this project.
RESERVED_LOGINS = {
    "system",
    "null",
    "undefined",
    "none",
}


class ValidationError(ApplicationClientError):
    """Custom validation error for all field validations.

    Inherits from ApplicationClientError for proper exception hierarchy integration.
    The exception_to_http_response handler converts this to HTTP 400 Bad Request.
    """


class PasswordValidationError(ValidationError):
    """Exception raised when password validation fails."""


def validate_not_empty(value: str) -> str:
    cleaned = value.strip()

    if not cleaned:
        msg = "Value cannot be empty"
        raise ValidationError(msg)

    return cleaned


def validate_length(value: str, min_length: int = 0, max_length: int | None = None) -> str:
    if len(value) < min_length:
        msg = f"Must be at least {min_length} characters"
        raise ValidationError(msg)

    if max_length and len(value) > max_length:
        msg = f"Must not exceed {max_length} characters"
        raise ValidationError(msg)

    return value


def validate_name(value: str) -> str:
    name = NAME_WHITESPACE_PATTERN.sub(" ", value.strip())

    if len(name) < NAME_MIN_LENGTH:
        msg = "Name cannot be empty"
        raise ValidationError(msg)

    if len(name) > NAME_MAX_LENGTH:
        msg = f"Name must not exceed {NAME_MAX_LENGTH} characters"
        raise ValidationError(msg)

    if not NAME_VALID_PATTERN.fullmatch(name):
        msg = "Name contains invalid characters"
        raise ValidationError(msg)

    if NAME_REPEATED_PATTERN.search(name):
        msg = "Name contains suspicious repeated characters"
        raise ValidationError(msg)

    return name


def validate_login(value: str) -> str:
    login = value.strip().lower()

    if len(login) < LOGIN_MIN_LENGTH:
        msg = f"Login must be at least {LOGIN_MIN_LENGTH} characters"
        raise ValidationError(msg)

    if len(login) > LOGIN_MAX_LENGTH:
        msg = f"Login must not exceed {LOGIN_MAX_LENGTH} characters"
        raise ValidationError(msg)

    if not LOGIN_VALID_PATTERN.fullmatch(login):
        msg = (
            "Login must start with a letter or number and may only contain "
            "lowercase letters, numbers, dots, hyphens, and underscores"
        )
        raise ValidationError(msg)

    if login in RESERVED_LOGINS:
        msg = "Login is reserved and cannot be used"
        raise ValidationError(msg)

    if LOGIN_REPEATED_PATTERN.search(login):
        msg = "Login contains too many repeated characters"
        raise ValidationError(msg)

    return login


def validate_password(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        msg = f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
        raise PasswordValidationError(msg)

    if len(value) > PASSWORD_MAX_LENGTH:
        msg = f"Password must not exceed {PASSWORD_MAX_LENGTH} characters"
        raise PasswordValidationError(msg)

    if not PASSWORD_UPPERCASE_PATTERN.search(value):
        msg = "Password must contain at least one uppercase letter"
        raise PasswordValidationError(msg)

    if not PASSWORD_LOWERCASE_PATTERN.search(value):
        msg = "Password must contain at least one lowercase letter"
        raise PasswordValidationError(msg)

    if not PASSWORD_DIGIT_PATTERN.search(value):
        msg = "Password must contain at least one digit"
        raise PasswordValidationError(msg)

    if not PASSWORD_SPECIAL_PATTERN.search(value):
        msg = "Password must contain at least one special character"
        raise PasswordValidationError(msg)

    if PASSWORD_PREDICTABLE_START_PATTERN.match(value):
        msg = "Password is too common - please choose a more unique password"
        raise PasswordValidationError(msg)

    return value


GENERATED_PASSWORD_LENGTH = 20
# No quotes, $, backslash or spaces, so the password is copied from a terminal as is.
_GENERATED_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#%^*-_=+"


def generate_password() -> str:
    """Return a random password that passes ``validate_password``."""
    while True:
        password = "".join(secrets.choice(_GENERATED_PASSWORD_ALPHABET) for _ in range(GENERATED_PASSWORD_LENGTH))
        try:
            return validate_password(password)
        except PasswordValidationError:
            continue
