"""Seeded retest decisions and routing."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from pak_simulator.model import Retest
from pak_simulator.simulation.state import Unit


@dataclass(frozen=True, slots=True)
class RetestDecision:
    """Queue placement for a failed unit that is due for another attempt."""

    only_slot: int | None
    avoid_slot: int | None

    @property
    def in_place(self) -> bool:
        return self.only_slot is not None


class RetestPolicy:
    """Decide whether a failed attempt is retried and where it is routed."""

    def __init__(self, settings: Retest, slot_count: int, rng_for_unit: Callable[[Unit], random.Random]) -> None:
        self._settings = settings
        self._slot_count = slot_count
        self._rng_for_unit = rng_for_unit

    def decide(self, unit: Unit, failed_slot: int, *, same_slot_only: bool = False) -> RetestDecision | None:
        """Return a seeded retry route, or ``None`` when no retry is due.

        The chance draw is followed by a placement draw for independent,
        multi-slot runs. This keeps the established seeded decisions while
        naming both draws instead of relying on an unexplained skipped draw.
        """
        if unit.attempt >= self._settings.max_attempts:
            return None

        rng = self._rng_for_unit(unit)
        if rng.random() >= self._settings.chance:
            return None

        in_place = same_slot_only or self._slot_count == 1 or rng.random() >= self._settings.other_slot

        return RetestDecision(
            only_slot=failed_slot if in_place else None,
            avoid_slot=None if in_place else failed_slot,
        )
