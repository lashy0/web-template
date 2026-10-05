"""Errors intended for the author of a scenario."""

from pydantic import ValidationError


class ScenarioError(Exception):
    """The scenario cannot be loaded or compiled."""


def validation_message(exc: ValidationError) -> str:
    """Include field paths and reasons without echoing credentials from input."""
    messages = []

    for error in exc.errors(include_input=False, include_context=False, include_url=False):
        path = "$"

        for part in error["loc"]:
            path += f".{part}" if isinstance(part, str) and part.isidentifier() else f"[{part!r}]"

        messages.append(f"{path}: {error['msg'].removeprefix('Value error, ')}")

    return "\n".join(messages)
