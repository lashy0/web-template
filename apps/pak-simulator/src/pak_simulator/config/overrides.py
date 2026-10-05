"""Apply run overrides to an immutable compiled scenario."""

from __future__ import annotations

from dataclasses import replace

from pydantic import TypeAdapter, ValidationError

from pak_simulator.config.errors import validation_message
from pak_simulator.config.spec import Probability, TimeSpec
from pak_simulator.model import Simulation
from pak_simulator.values import Span

_TIME = TypeAdapter(TimeSpec)
_PROBABILITY = TypeAdapter(Probability)


class RunOptionError(ValueError):
    """An invalid override, with its option name for the caller's error reporting."""

    def __init__(self, message: str, *, option: str) -> None:
        super().__init__(message)
        self.option = option


def configure_run(
    simulation: Simulation,
    *,
    pass_rate: float | None = None,
    start_delay: str | None = None,
    session_delay: str | None = None,
) -> Simulation:
    """Apply overrides without modifying the source scenario or its profiles."""
    if pass_rate is not None:
        try:
            pass_rate = _PROBABILITY.validate_python(pass_rate)
        except ValidationError as exc:
            raise RunOptionError("Use a probability from 0 to 1.", option="--pass-rate") from exc

    sessions = replace(
        simulation.sessions,
        start=_delay(start_delay, "--start-delay") if start_delay is not None else simulation.sessions.start,
        swap=_delay(session_delay, "--session-delay") if session_delay is not None else simulation.sessions.swap,
    )
    profiles = {pak.profile.key: pak.profile for pak in simulation.paks}

    if pass_rate is not None:
        profiles = {key: replace(profile, pass_rate=pass_rate) for key, profile in profiles.items()}

    configured = tuple(
        replace(pak, profile=profiles[pak.profile.key]) if pass_rate is not None else pak for pak in simulation.paks
    )

    return replace(
        simulation,
        sessions=sessions,
        paks=configured,
        profiles=tuple(profiles.get(profile.key, profile) for profile in simulation.profiles),
    )


def _delay(value: str, option: str) -> Span:
    try:
        return _TIME.validate_python(value)
    except ValidationError as exc:
        raise RunOptionError(
            validation_message(exc).removeprefix("$: "),
            option=option,
        ) from exc
