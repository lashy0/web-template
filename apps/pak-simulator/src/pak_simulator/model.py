"""The simulation a scenario describes, and the sessions it plays."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pak_simulator.values import Span


@dataclass(frozen=True, slots=True)
class Check:
    """A check of the PAK profile, as a healthy KG unit passes it."""

    name: str
    label: str
    group: str
    time: Span
    value: Span | None
    unit: str | None
    low: float | None
    high: float | None
    critical: bool

    def within_limits(self, value: float | None) -> bool | None:
        """Whether the value meets the limits; ``None`` for a check without limits."""
        if self.low is None and self.high is None:
            return None

        if value is None:
            return False

        return (self.low is None or value >= self.low) and (self.high is None or value <= self.high)


@dataclass(frozen=True, slots=True)
class Effect:
    """How a defect changes one check; unset fields keep the check's own."""

    value: Span | None = None
    name: str | None = None
    label: str | None = None
    time: Span | None = None
    passed: bool | None = None


@dataclass(frozen=True, slots=True)
class Defect:
    key: str
    chance: float
    persists: float
    effects: Mapping[str, Effect]
    """Effects by the check name or label they apply to."""
    transient: bool = False
    """A condition of the test rather than of the unit, rolled anew for every session."""

    def effect_on(self, check: Check) -> Effect | None:
        return self.effects.get(check.label) or self.effects.get(check.name)


@dataclass(frozen=True, slots=True)
class PlannedStep:
    """A step as the PAK will report it."""

    no: int
    name: str
    label: str
    group: str
    duration: float
    value: float | None
    unit: str | None
    low: float | None
    high: float | None
    passed: bool
    critical: bool


@dataclass(frozen=True, slots=True)
class Profile:
    key: str
    firmware_version: str
    checks: tuple[Check, ...]
    defects: tuple[Defect, ...]
    pass_rate: float | None = None


@dataclass(frozen=True, slots=True)
class Retest:
    chance: float
    other_slot: float
    max_attempts: int
    pause: Span


@dataclass(frozen=True, slots=True)
class Sessions:
    start: Span
    swap: Span
    abandon: float
    retest: Retest
    together: bool = False
    """Slots are loaded all at once and reloaded when every one has finished."""


@dataclass(frozen=True, slots=True)
class Pak:
    code: str
    client_id: str
    access_key: str
    slots: int
    profile: Profile
    dev_euis: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Simulation:
    server: str
    verify_tls: bool
    sessions: Sessions
    paks: tuple[Pak, ...]
    profiles: tuple[Profile, ...]
