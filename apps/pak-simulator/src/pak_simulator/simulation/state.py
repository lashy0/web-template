"""Runtime state, attempt statistics and recent simulator events."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pak_simulator.model import PlannedStep
from pak_simulator.simulation.statistics import RunStatsSnapshot

Level = Literal["info", "warning", "error"]
Clock = Callable[[], float]


def format_dev_eui(dev_eui: str) -> str:
    return " ".join(dev_eui[index : index + 4] for index in range(0, len(dev_eui), 4))


class PakStatus(StrEnum):
    RUNNING = "running"
    WAITING = "waiting"
    FINISHED = "finished"
    STOPPED = "stopped"
    ERROR = "error"


class SlotStatus(StrEnum):
    WAITING = "waiting"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    ABORTED = "aborted"
    ERROR = "error"
    DONE = "done"


class AttemptOutcome(StrEnum):
    """Result of an attempt, separate from a slot's display lifecycle."""

    PASSED = "passed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    SKIPPED = "skipped"
    ERROR = "error"

    @property
    def slot_status(self) -> SlotStatus | None:
        """Return the terminal slot status for attempts that opened a session."""
        match self:
            case AttemptOutcome.PASSED:
                return SlotStatus.PASSED
            case AttemptOutcome.FAILED:
                return SlotStatus.FAILED
            case AttemptOutcome.ABANDONED:
                return SlotStatus.ABANDONED
            case AttemptOutcome.ERROR:
                return SlotStatus.ERROR
            case AttemptOutcome.SKIPPED:
                return None


@dataclass
class SlotState:
    """What a slot shows on the screen."""

    no: int
    clock: Clock = field(default=time.monotonic, repr=False, compare=False, kw_only=True)
    status: SlotStatus = SlotStatus.WAITING
    dev_eui: str | None = None
    attempt: int = 0
    total_steps: int = 0
    outcomes: list[bool] = field(default_factory=list)
    """Results of the completed steps."""
    step_label: str = ""
    failed_labels: list[str] = field(default_factory=list)
    started_at: float | None = None
    finished_at: float | None = None
    note: str = ""
    next_session_at: float | None = None

    @property
    def next_session_in(self) -> float | None:
        if self.next_session_at is None:
            return None

        return max(0.0, self.next_session_at - self.clock())

    @property
    def elapsed(self) -> float | None:
        if self.started_at is None:
            return None

        end = self.finished_at if self.finished_at is not None else self.clock()

        return end - self.started_at

    @property
    def failure_summary(self) -> str:
        """The first failed check and the number of additional failures."""
        if not self.failed_labels:
            return ""

        first = self.failed_labels[0]
        remaining = len(self.failed_labels) - 1

        return f"{first} (+{remaining} more)" if remaining else first

    def begin(self, unit: Unit, total_steps: int) -> None:
        self.status = SlotStatus.RUNNING
        self.dev_eui = unit.dev_eui
        self.attempt = unit.attempt
        self.total_steps = total_steps
        self.outcomes = []
        self.step_label = "Opening the session"
        self.failed_labels = []
        self.started_at = self.clock()
        self.finished_at = None
        self.note = ""
        self.next_session_at = None

    def step_started(self, step: PlannedStep) -> None:
        self.step_label = step.label

    def step_completed(self, step: PlannedStep) -> None:
        self.outcomes.append(step.passed)

        if not step.passed:
            self.failed_labels.append(step.label)

    def end(self, status: SlotStatus, note: str = "") -> None:
        self.status = status
        self.step_label = ""

        if self.finished_at is None:
            self.finished_at = self.clock()

        self.note = note

    def clear(self) -> None:
        """Empty the slot: the unit never got a session."""
        self.status = SlotStatus.WAITING
        self.dev_eui = None
        self.attempt = 0
        self.total_steps = 0
        self.outcomes = []
        self.step_label = ""
        self.failed_labels = []
        self.started_at = self.finished_at = None
        self.note = ""
        self.next_session_at = None


@dataclass
class Unit:
    """A KG unit in the operator's hands."""

    dev_eui: str
    cycle: int = 0
    attempt: int = 0
    defects: frozenset[str] | None = None
    only_slot: int | None = None
    """A retest in the slot the unit failed in."""
    avoid_slot: int | None = None
    """A retest moved to another slot."""


@dataclass(frozen=True, slots=True)
class Event:
    at: datetime
    pak: str
    slot: int | None
    text: str
    level: Level
    topic: str | None = None
    """Consecutive events of a topic replace one another on the screen."""
    dev_eui: str | None = None
    result: SlotStatus | None = None


@dataclass(frozen=True, slots=True)
class EventLogSnapshot:
    recent: tuple[Event, ...]
    limit: int | None


class EventSinkError(Exception):
    """The shared event output failed; it must stop the whole simulation."""


class EventLog:
    def __init__(self, *, size: int = 8, sink: Callable[[Event], None] | None = None) -> None:
        self.recent: deque[Event] = deque(maxlen=size)
        self._sink = sink

    def snapshot(self) -> EventLogSnapshot:
        return EventLogSnapshot(tuple(self.recent), self.recent.maxlen)

    def add(self, event: Event) -> None:
        if event.topic is not None and self.recent and self.recent[-1].topic == event.topic:
            self.recent[-1] = event
        else:
            self.recent.append(event)

        if self._sink is not None:
            try:
                self._sink(event)
            except Exception as exc:
                raise EventSinkError("Simulator event output failed") from exc


@dataclass(frozen=True, slots=True)
class RunResult:
    pak_code: str
    status: PakStatus
    completed_attempts: int
    failed_attempts: int
    abandoned_attempts: int
    skipped_attempts: int
    execution_errors: int
    processed_units: int
    unfinished_units: int

    @property
    def successful(self) -> bool:
        """Failed checks are simulation outcomes; execution errors fail the run."""
        return self.status is PakStatus.FINISHED and not self.execution_errors and not self.unfinished_units


@dataclass(frozen=True, slots=True)
class SlotSnapshot:
    no: int
    status: SlotStatus
    dev_eui: str | None
    attempt: int
    total_steps: int
    outcomes: tuple[bool, ...]
    step_label: str
    failure_summary: str
    elapsed: float | None
    next_session_in: float | None
    note: str

    @classmethod
    def from_state(cls, slot: SlotState) -> SlotSnapshot:
        return cls(
            slot.no,
            slot.status,
            slot.dev_eui,
            slot.attempt,
            slot.total_steps,
            tuple(slot.outcomes),
            slot.step_label,
            slot.failure_summary,
            slot.elapsed,
            slot.next_session_in,
            slot.note,
        )


@dataclass(frozen=True, slots=True)
class PakSnapshot:
    code: str
    profile_key: str
    pass_rate: float | None
    total_units: int
    status: PakStatus
    slots: tuple[SlotSnapshot, ...]
    stats: RunStatsSnapshot
    alert: str | None
    looping: bool
    processed_units: int
    running_units: int
    waiting_units: int
    queued_units: int
    next_load_in: float | None
    actual_pass_rate: float | None
