"""Numeric value objects used by simulation models."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Span:
    """A fixed number or a uniform range, rounded to ``decimals`` places."""

    low: float
    high: float
    decimals: int | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.low) or not math.isfinite(self.high):
            raise ValueError("Range endpoints must be finite numbers")

        if self.low > self.high:
            raise ValueError("The range starts above its end")

    def sample(self, rng: random.Random) -> float:
        if self.high > self.low:
            if math.isfinite(self.high - self.low):
                value = rng.uniform(self.low, self.high)
            else:
                # Opposite-sign finite endpoints can overflow their difference.
                fraction = rng.random()
                value = self.low * (1 - fraction) + self.high * fraction
        else:
            value = self.low

        if self.decimals is not None:
            value = round(value, self.decimals)

        return min(self.high, max(self.low, value))

    @property
    def middle(self) -> float:
        return self.low / 2 + self.high / 2
