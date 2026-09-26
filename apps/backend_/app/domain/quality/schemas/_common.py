"""Validation shared by the defect catalog schemas."""

from app.lib.validation import ValidationError, validate_length, validate_not_empty

NAME_MAX_LENGTH = 255
TEXT_MAX_LENGTH = 2000


def validate_code(value: str, *, max_length: int) -> str:
    """Return a code without surrounding whitespace; it may not contain any inside."""
    code = validate_length(validate_not_empty(value), max_length=max_length)

    if any(character.isspace() for character in code):
        msg = "Code cannot contain whitespace"
        raise ValidationError(msg)

    return code


def validate_title(value: str, *, max_length: int = NAME_MAX_LENGTH) -> str:
    """Return a required text without surrounding whitespace."""
    return validate_length(validate_not_empty(value), max_length=max_length)


def validate_text(value: str) -> str:
    return validate_length(value, max_length=TEXT_MAX_LENGTH)
