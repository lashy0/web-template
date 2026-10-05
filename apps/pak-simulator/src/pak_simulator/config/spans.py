"""Times and values written in a scenario as a number or a ``low..high`` range."""

from __future__ import annotations

import re

from pak_simulator.values import Span

_TIME = r"\d+(?:\.\d+)?(?:ms|s|m)?"
TIME_PATTERN = rf"^{_TIME}(?:\.\.{_TIME})?$"
"""``25s``, ``1.5m``, ``500ms``, ``24s..27s``; a bare number is seconds."""

_NUMBER = r"-?\d+(?:\.\d+)?"
VALUE_PATTERN = rf"^{_NUMBER}(?:\.\.{_NUMBER})?$"
"""``-1``, ``205..225``, ``190.0..223.5``, ``-73..-56``."""

_TIME_UNITS = {"ms": 0.001, "s": 1.0, "m": 60.0}


class SpanError(ValueError):
    """A range whose low end exceeds the high end."""


def _checked(low: float, high: float, decimals: int | None, text: str) -> Span:
    if low > high:
        msg = f"{text!r}: the range starts above its end"
        raise SpanError(msg)

    try:
        return Span(low, high, decimals)
    except ValueError as exc:
        raise SpanError(f"{text!r}: {exc}") from exc


def _seconds(text: str) -> float:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s|m)?", text)

    if match is None:
        raise SpanError(f"{text!r}: expected a nonnegative time")

    return float(match[1]) * _TIME_UNITS[match[2] or "s"]


def parse_time(spec: float | str) -> Span:
    """Seconds from ``25``, ``25s``, ``1.5m`` or ``24s..27s``."""
    if isinstance(spec, float | int):
        if spec < 0:
            raise SpanError("Time must be nonnegative")

        return _checked(float(spec), float(spec), None, str(spec))

    if not re.fullmatch(TIME_PATTERN, spec):
        raise SpanError(f"{spec!r}: expected a nonnegative time or range")

    low, _, high = spec.partition("..")

    return _checked(_seconds(low), _seconds(high or low), None, spec)


def _decimals(text: str) -> int:
    _, _, fraction = text.partition(".")

    return len(fraction)


def parse_value(spec: float | str) -> Span:
    """A measurement from ``-1``, ``205..225`` or ``190.0..223.5``.

    Samples keep as many decimals as the range is written with, so
    ``205..225`` gives whole numbers and ``190.0..223.5`` one decimal.
    """
    if isinstance(spec, float | int):
        value = float(spec)

        return _checked(value, value, 0 if value.is_integer() else None, str(spec))

    if not re.fullmatch(VALUE_PATTERN, spec):
        raise SpanError(f"{spec!r}: expected a number or numeric range")

    low, _, high = spec.partition("..")
    high = high or low

    return _checked(float(low), float(high), max(_decimals(low), _decimals(high)), spec)
