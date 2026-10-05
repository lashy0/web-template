"""Generate session outcomes and matching verification steps."""

from __future__ import annotations

import math
import random
from dataclasses import replace

from pak_simulator.model import Check, Defect, Effect, PlannedStep, Profile


def prepare_session(
    profile: Profile,
    rng: random.Random,
    previous: frozenset[str] | None = None,
) -> tuple[frozenset[str], list[PlannedStep]]:
    """Choose the session outcome and prepare matching check results."""
    if profile.pass_rate is not None and rng.random() < profile.pass_rate:
        steps = plan_session(profile, rng, frozenset())

        return frozenset(), [_force_result(step, passed=True) for step in steps]

    defects = roll_defects(profile, rng, previous)
    steps = plan_session(profile, rng, defects)

    if profile.pass_rate is None or any(not step.passed for step in steps):
        return defects, steps

    # A chosen failed session must have a failed check, even if the random
    # defect roll produced none. Prefer the profile's own failure values.
    candidates: list[tuple[Defect, list[PlannedStep]]] = []

    for defect in profile.defects:
        if defect.chance <= 0:
            continue

        failure = plan_session(profile, rng, frozenset({defect.key}))

        if any(not step.passed for step in failure):
            candidates.append((defect, failure))

    if candidates:
        defect, steps = rng.choices(candidates, weights=[item.chance for item, _ in candidates])[0]

        return frozenset({defect.key}), steps

    # Profiles without usable defects can still request a failed session.
    index = rng.randrange(len(steps))
    steps[index] = _force_result(steps[index], passed=False)

    return defects, steps


def roll_defects(
    profile: Profile,
    rng: random.Random,
    previous: frozenset[str] | None = None,
) -> frozenset[str]:
    """Defects of a session: new ones at their chance, or on a retest the ones that persist.

    Transient defects are rolled at their chance for every session.
    """
    return frozenset(
        defect.key
        for defect in profile.defects
        if (
            rng.random() < defect.chance
            if previous is None or defect.transient
            else defect.key in previous and rng.random() < defect.persists
        )
    )


def plan_session(profile: Profile, rng: random.Random, defects: frozenset[str]) -> list[PlannedStep]:
    """Every step of a session; the runner stops early after a failed critical step."""
    active = [defect for defect in profile.defects if defect.key in defects]
    steps: list[PlannedStep] = []

    for no, check in enumerate(profile.checks, start=1):
        effects = [effect for defect in active if (effect := defect.effect_on(check)) is not None]
        steps.append(_plan_step(no, check, effects, rng))

    return steps


def _force_result(step: PlannedStep, *, passed: bool) -> PlannedStep:
    """Keep measurement values consistent with an explicitly chosen result."""
    value = step.value

    if passed:
        if step.low is not None and (value is None or value < step.low):
            value = step.low

        if step.high is not None and (value is None or value > step.high):
            value = step.high
    elif step.low is not None or step.high is not None:
        value = _failure_value(step.low, step.high)
    else:
        value = -1

    return replace(step, passed=passed, value=value)


def _failure_value(low: float | None, high: float | None) -> float | None:
    """Choose a finite out-of-bounds value, or omit an impossible measurement."""
    for boundary, direction in ((low, -1.0), (high, 1.0)):
        if boundary is None:
            continue

        value = boundary + direction

        if value == boundary or not math.isfinite(value):
            value = math.nextafter(boundary, math.copysign(math.inf, direction))

        if math.isfinite(value):
            return value
    # No finite value is outside these limits; a missing measurement fails them.
    return None


def _plan_step(no: int, check: Check, effects: list[Effect], rng: random.Random) -> PlannedStep:
    name, label, time, value_span = check.name, check.label, check.time, check.value
    forced: bool | None = None

    for effect in effects:
        name = effect.name or name
        label = effect.label or label
        time = effect.time or time
        value_span = effect.value or value_span
        forced = effect.passed if effect.passed is not None else forced

    value = value_span.sample(rng) if value_span is not None else None

    if forced is not None:
        passed = forced
    elif (within := check.within_limits(value)) is not None:
        passed = within
    else:
        # A check without limits fails only by a defect.
        passed = not effects

    return PlannedStep(
        no=no,
        name=name,
        label=label,
        group=check.group,
        duration=time.sample(rng),
        value=value,
        unit=check.unit,
        low=check.low,
        high=check.high,
        passed=passed,
        critical=check.critical,
    )
