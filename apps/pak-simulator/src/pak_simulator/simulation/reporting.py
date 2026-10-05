"""Record attempt outcomes and turn them into operator-facing events."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from pak_simulator.errors import ApiError, error_message
from pak_simulator.simulation.state import (
    AttemptOutcome,
    Event,
    EventLog,
    Level,
    SlotState,
    SlotStatus,
    Unit,
    format_dev_eui,
)
from pak_simulator.simulation.statistics import RunStats

_RESULT_MESSAGES: dict[SlotStatus, tuple[str, Level]] = {
    SlotStatus.PASSED: ("All checks passed", "info"),
    SlotStatus.FAILED: ("First failed check: {failure_summary}", "warning"),
    SlotStatus.ABANDONED: ("The operator took the unit out", "warning"),
}


class AttemptReporter:
    """Update attempt counts and write the matching simulator events."""

    def __init__(self, pak_code: str, events: EventLog, stats: RunStats) -> None:
        self._pak_code = pak_code
        self._events = events
        self._stats = stats
        self._skipped_by_code: Counter[str] = Counter()

    def finished(self, slot: SlotState, unit: Unit, outcome: AttemptOutcome, note: str = "") -> None:
        status = outcome.slot_status
        assert status is not None

        slot.end(status, note)

        match status:
            case SlotStatus.PASSED:
                self._stats.record_passed()
            case SlotStatus.FAILED:
                self._stats.record_failed()
            case SlotStatus.ABANDONED:
                self._stats.record_abandoned()
            case _:
                raise ValueError(f"Not a completed attempt result: {status}")

        message, level = _RESULT_MESSAGES[status]
        attempt = f"Attempt {unit.attempt} · " if unit.attempt > 1 else ""
        self.log(
            slot.no,
            f"{attempt}{message.format(failure_summary=slot.failure_summary)}",
            level,
            dev_eui=unit.dev_eui,
            result=status,
        )

    def skipped(self, slot: SlotState, unit: Unit, exc: ApiError) -> None:
        code = exc.code
        assert code is not None

        self._stats.record_skipped()
        self._skipped_by_code[code] += 1
        slot.clear()
        self.log(
            None,
            f"{error_message(exc)} Units skipped: {self._skipped_by_code[code]}; last {format_dev_eui(unit.dev_eui)}.",
            "warning",
            topic=f"skipped:{code}",
        )

    def access_error(self, slot: SlotState, message: str, *, announce: bool) -> None:
        if announce:
            self.log(None, message, "error", result=SlotStatus.ERROR)

        self._stats.record_error()
        slot.end(SlotStatus.ERROR, message)

    def execution_error(self, slot: SlotState, message: str) -> AttemptOutcome:
        self._stats.record_error()
        slot.end(SlotStatus.ERROR, message)
        self.log(slot.no, message, "error", dev_eui=slot.dev_eui, result=SlotStatus.ERROR)

        return AttemptOutcome.ERROR

    def cleanup_error(self, message: str) -> None:
        self._stats.record_cleanup_error()
        self.log(None, message, "error")

    def log(
        self,
        slot: int | None,
        text: str,
        level: Level,
        *,
        topic: str | None = None,
        dev_eui: str | None = None,
        result: SlotStatus | None = None,
    ) -> None:
        self._events.add(
            Event(
                datetime.now(),
                self._pak_code,
                slot,
                text,
                level,
                f"{self._pak_code}:{topic}" if topic else None,
                dev_eui,
                result,
            )
        )
