"""Production-ready field validation utilities with comprehensive security checks."""

import hashlib
import re
from typing import Annotated, Any

import msgspec

from app.lib.exceptions import ApplicationClientError

NAME_WHITESPACE_PATTERN = re.compile(r"\s+")
NAME_VALID_PATTERN = re.compile(
    r"^[a-zA-ZÀ-ÿĀ-žА-яЁё\s'.-]+$"
)
NAME_REPEATED_PATTERN = re.compile(r"(.)\1{4,}")

LOGIN_VALID_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9._-]*$"
)
LOGIN_REPEATED_PATTERN = re.compile(r"(.)\1{3,}")

PASSWORD_UPPERCASE_PATTERN = re.compile(r"[A-Z]")
PASSWORD_LOWERCASE_PATTERN = re.compile(r"[a-z]")
PASSWORD_DIGIT_PATTERN = re.compile(r"\d")
PASSWORD_SPECIAL_PATTERN = re.compile(
    r"""[!@#$%^&*(),.?":{}|<>_+=\-\[\]\\/~`]"""
)
PASSWORD_SIMPLE_REPEATED_PATTERN = re.compile(r"^(.)\1{11,}$")
PASSWORD_SEQUENTIAL_PATTERN = re.compile(
    r"^(012|123|234|345|456|567|678|789|890|abc|bcd|cde)",
    re.IGNORECASE,
)
PASSWORD_KEYBOARD_PATTERN = re.compile(
    r"^(qwe|asd|zxc)",
    re.IGNORECASE,
)


NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 128

LOGIN_MIN_LENGTH = 3
LOGIN_MAX_LENGTH = 64

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
PASSWORD_STRONG_LENGTH = 16
PASSWORD_VERY_STRONG_LENGTH = 20

PASSWORD_SCORE_MEDIUM = 5
PASSWORD_SCORE_STRONG = 7


# `admin`, `administrator`, etc. intentionally are NOT reserved:
# they are valid application logins for this project.
RESERVED_LOGINS = {
    "system",
    "null",
    "undefined",
    "none",
}

COMMON_PASSWORDS = {
    "password",
    "password123",
    "password1234",
    "password12345",
    "123456789",
    "qwertyuiop",
    "administrator",
    "welcome123",
    "letmein123",
    "admin123456",
}

COMMON_PASSWORD_HASHES = {
    hashlib.sha256(password.encode()).hexdigest()
    for password in COMMON_PASSWORDS
}


class ValidationError(ApplicationClientError):
    """Custom validation error for all field validations.

    Inherits from ApplicationClientError for proper exception hierarchy integration.
    The exception_to_http_response handler converts this to HTTP 400 Bad Request.
    """


class PasswordValidationError(ValidationError):
    """Exception raised when password validation fails."""



def _ensure_str(value: Any, field_name: str, exc_type: type[ValidationError] = ValidationError) -> str:
    """Ensure the value is a string.

    Args:
        value: The value to validate.
        field_name: Field label used in error messages.
        exc_type: Exception type to raise on validation failure.

    Returns:
        The validated string.
    """
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"

        raise exc_type(msg)

    return value


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
    value = _ensure_str(value, "Name")

    name = value.strip()
    name = NAME_WHITESPACE_PATTERN.sub(" ", name)

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
    value = _ensure_str(value, "Login")

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


def _is_common_password(password: str) -> bool:
    password_lower = password.lower()

    if password_lower in COMMON_PASSWORDS:
        return True

    if PASSWORD_SIMPLE_REPEATED_PATTERN.match(password):
        return True

    if PASSWORD_SEQUENTIAL_PATTERN.match(password_lower):
        return True

    return bool(PASSWORD_KEYBOARD_PATTERN.match(password_lower))


def validate_password_strength(password: str) -> None:
    password = _ensure_str(
        password,
        "Password",
        PasswordValidationError,
    )

    if len(password) < PASSWORD_MIN_LENGTH:
        msg = (
            f"Password must be at least "
            f"{PASSWORD_MIN_LENGTH} characters long"
        )
        raise PasswordValidationError(msg)

    if len(password) > PASSWORD_MAX_LENGTH:
        msg = (
            f"Password must not exceed "
            f"{PASSWORD_MAX_LENGTH} characters"
        )
        raise PasswordValidationError(msg)

    if not PASSWORD_UPPERCASE_PATTERN.search(password):
        msg = "Password must contain at least one uppercase letter"
        raise PasswordValidationError(msg)

    if not PASSWORD_LOWERCASE_PATTERN.search(password):
        msg = "Password must contain at least one lowercase letter"
        raise PasswordValidationError(msg)

    if not PASSWORD_DIGIT_PATTERN.search(password):
        msg = "Password must contain at least one digit"
        raise PasswordValidationError(msg)

    if not PASSWORD_SPECIAL_PATTERN.search(password):
        msg = "Password must contain at least one special character"
        raise PasswordValidationError(msg)

    if _is_common_password(password):
        msg = "Password is too common - please choose a more unique password"
        raise PasswordValidationError(msg)


def validate_password(value: str) -> str:
    value = _ensure_str(
        value,
        "Password",
        PasswordValidationError,
    )

    validate_password_strength(value)

    password_hash = hashlib.sha256(value.encode()).hexdigest()

    if password_hash in COMMON_PASSWORD_HASHES:
        msg = "Password is too common, please choose a different one"
        raise PasswordValidationError(msg)

    return value


def get_password_strength(password: str) -> dict[str, Any]:
    """Get detailed password strength analysis.

    Args:
        password: The password to analyze.

    Returns:
        Dictionary with strength analysis.
    """
    analysis: dict[str, Any] = {
        "score": 0,
        "strength": "weak",
        "requirements": {
            "length": len(password) >= PASSWORD_MIN_LENGTH,
            "uppercase": bool(PASSWORD_UPPERCASE_PATTERN.search(password)),
            "lowercase": bool(PASSWORD_LOWERCASE_PATTERN.search(password)),
            "digits": bool(PASSWORD_DIGIT_PATTERN.search(password)),
            "special_chars": bool(PASSWORD_SPECIAL_PATTERN.search(password)),
            "not_common": not _is_common_password(password),
        },
        "feedback": [],
    }

    if analysis["requirements"]["length"]:
        analysis["score"] += 2
    else:
        analysis["feedback"].append("Use at least 12 characters")

    if analysis["requirements"]["uppercase"]:
        analysis["score"] += 1
    else:
        analysis["feedback"].append("Include uppercase letters")

    if analysis["requirements"]["lowercase"]:
        analysis["score"] += 1
    else:
        analysis["feedback"].append("Include lowercase letters")

    if analysis["requirements"]["digits"]:
        analysis["score"] += 1
    else:
        analysis["feedback"].append("Include numbers")

    if analysis["requirements"]["special_chars"]:
        analysis["score"] += 1
    else:
        analysis["feedback"].append("Include special characters (!@#$%^&*)")

    if analysis["requirements"]["not_common"]:
        analysis["score"] += 1
    else:
        analysis["feedback"].append("Avoid common passwords")

    if len(password) >= PASSWORD_STRONG_LENGTH:
        analysis["score"] += 1
    if len(password) >= PASSWORD_VERY_STRONG_LENGTH:
        analysis["score"] += 1

    if analysis["score"] >= PASSWORD_SCORE_STRONG:
        analysis["strength"] = "strong"
    elif analysis["score"] >= PASSWORD_SCORE_MEDIUM:
        analysis["strength"] = "medium"
    else:
        analysis["strength"] = "weak"

    return analysis


Name = Annotated[
    str,
    msgspec.Meta(
        description="Human name (1-128 characters)",
    ),
]

Login = Annotated[
    str,
    msgspec.Meta(
        description=(
            "Kratos login (3-64 characters, lowercase alphanumeric/dots/hyphens/underscores)"
        ),
    ),
]

Password = Annotated[
    str,
    msgspec.Meta(
        description=(
            "Strong password (12+ characters, mixed case, number and special character)"
        ),
    ),
]
