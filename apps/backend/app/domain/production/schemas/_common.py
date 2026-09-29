"""Validation shared by production catalog and order schemas."""

from typing import Annotated

import msgspec

from app.lib.validation import validate_length, validate_not_empty

NAME_MAX_LENGTH = 128
DESCRIPTION_MAX_LENGTH = 2000

Title = Annotated[str, msgspec.Meta(min_length=1, max_length=NAME_MAX_LENGTH)]
Description = Annotated[str, msgspec.Meta(max_length=DESCRIPTION_MAX_LENGTH)]


def validate_title(value: str, *, max_length: int = NAME_MAX_LENGTH) -> str:
    """Return a required single-line text without surrounding whitespace."""
    return validate_length(validate_not_empty(value), max_length=max_length)


def validate_description(value: str) -> str:
    return validate_length(value, max_length=DESCRIPTION_MAX_LENGTH)
