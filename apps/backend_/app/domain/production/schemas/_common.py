"""Validation shared by production catalog and order schemas."""

from app.lib.validation import validate_length, validate_not_empty

NAME_MAX_LENGTH = 128
DESCRIPTION_MAX_LENGTH = 2000


def validate_title(value: str, *, max_length: int = NAME_MAX_LENGTH) -> str:
    """Return a required single-line text without surrounding whitespace."""
    return validate_length(validate_not_empty(value), max_length=max_length)


def validate_description(value: str) -> str:
    return validate_length(value, max_length=DESCRIPTION_MAX_LENGTH)
