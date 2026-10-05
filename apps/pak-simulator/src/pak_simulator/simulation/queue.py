"""Unit selection, reservations and retest routing, without I/O."""

from __future__ import annotations

from collections import Counter, deque

from pak_simulator.simulation.state import Unit


class UnitQueue:
    def __init__(self, dev_euis: tuple[str, ...], *, loop: bool) -> None:
        self._selected = frozenset(dev_euis)
        self._pool = deque(dev_euis)
        self._loop = loop
        self._loop_pool = set(dev_euis) if loop else set()
        self._retests: list[Unit] = []
        self._cycles: Counter[str] = Counter()
        self._busy: set[str] = set()
        self._active: set[str] = set()
        self._processed: set[str] = set()
        self._errors: set[str] = set()

    @property
    def queued(self) -> int:
        return len(self._pool) + len(self._retests)

    @property
    def processed(self) -> int:
        return len(self._processed)

    @property
    def running(self) -> int:
        return len(self._active)

    @property
    def waiting(self) -> int:
        if not self._loop:
            active_unprocessed = sum(dev_eui not in self._processed for dev_eui in self._active)
            return len(self._selected) - len(self._processed) - active_unprocessed

        # The loop pool already contains queued, reserved and running units.
        # Only retests/reservations outside that pool need separate counting.
        off_pool = {unit.dev_eui for unit in self._retests} | self._busy
        off_pool.difference_update(self._loop_pool)
        off_pool.difference_update(self._active)
        active_pooled = sum(dev_eui in self._loop_pool for dev_eui in self._active)

        return len(self._loop_pool) - active_pooled + len(off_pool)

    @property
    def unfinished(self) -> int:
        return len((self._selected - self._processed) | self._errors)

    def should_wait(self, *, can_retest: bool) -> bool:
        return bool(self._retests or (self._busy and (self._loop or can_retest)))

    def take(self, slot_no: int) -> Unit | None:
        for index, unit in enumerate(self._retests):
            if unit.dev_eui in self._busy or unit.avoid_slot == slot_no:
                continue

            if unit.only_slot is not None and unit.only_slot != slot_no:
                continue

            del self._retests[index]

            self._busy.add(unit.dev_eui)

            return unit

        retesting = {unit.dev_eui for unit in self._retests}

        for _ in range(len(self._pool)):
            dev_eui = self._pool.popleft()

            if self._loop:
                self._pool.append(dev_eui)

            if dev_eui not in self._busy and dev_eui not in retesting:
                unit = Unit(dev_eui, cycle=self._cycles[dev_eui])
                self._cycles[dev_eui] += 1
                self._busy.add(dev_eui)

                return unit

        return None

    def start(self, unit: Unit) -> None:
        self._busy.add(unit.dev_eui)
        self._active.add(unit.dev_eui)

    def finish(self, unit: Unit, *, error: bool) -> None:
        self.release(unit)
        self._processed.add(unit.dev_eui)

        if error:
            self._errors.add(unit.dev_eui)
        else:
            self._errors.discard(unit.dev_eui)

    def release(self, unit: Unit) -> None:
        self._busy.discard(unit.dev_eui)
        self._active.discard(unit.dev_eui)

    def retest(self, unit: Unit, *, only_slot: int | None, avoid_slot: int | None) -> None:
        unit.only_slot, unit.avoid_slot = only_slot, avoid_slot
        self._retests.append(unit)
        self._processed.discard(unit.dev_eui)

    def reserve_retest(self, unit: Unit) -> None:
        self._processed.discard(unit.dev_eui)
        self._busy.add(unit.dev_eui)

    def return_unit(self, unit: Unit) -> None:
        self.release(unit)

        if unit.dev_eui in self._processed or unit.dev_eui in self._pool:
            return

        if all(queued.dev_eui != unit.dev_eui for queued in self._retests):
            self._retests.insert(0, unit)

    def exclude(self, dev_eui: str) -> None:
        self._pool = deque(value for value in self._pool if value != dev_eui)
        self._loop_pool.discard(dev_eui)
