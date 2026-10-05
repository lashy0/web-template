from __future__ import annotations

import math
import random
import sys

import pytest

from pak_simulator.config.spans import SpanError, parse_time, parse_value
from pak_simulator.values import Span

pytestmark = pytest.mark.unit


def test_mixed_time_units_compile_to_seconds() -> None:
    assert parse_time("500ms..1s") == Span(0.5, 1)


@pytest.mark.parametrize("duration", ["3s..1s", "1s..", "1s\n", "bad"])
def test_invalid_time_rejected(duration: str) -> None:
    with pytest.raises(SpanError):
        parse_time(duration)


@pytest.mark.parametrize("value", ["2..1", "bad", float("inf"), float("nan")])
def test_invalid_value_rejected(value: str | float) -> None:
    with pytest.raises(SpanError):
        parse_value(value)


@pytest.mark.parametrize("decimals", [None, 0, 2])
def test_large_range_samples_remain_finite_and_in_bounds(decimals: int | None) -> None:
    span = Span(-sys.float_info.max, sys.float_info.max, decimals)
    rng = random.Random(4)

    for _ in range(100):
        value = span.sample(rng)
        assert math.isfinite(value) and span.low <= value <= span.high


def test_ordinary_range_samples_are_repeatable_varied_and_keep_precision() -> None:
    span = parse_value("203.33..231.00")
    assert span == Span(203.33, 231.00, 2)
    rng = random.Random(4)
    samples = [span.sample(rng) for _ in range(100)]
    repeated_rng = random.Random(4)

    assert samples == [span.sample(repeated_rng) for _ in range(100)]
    assert len(set(samples)) > 1
    assert all(span.low <= value <= span.high and value == round(value, 2) for value in samples)
