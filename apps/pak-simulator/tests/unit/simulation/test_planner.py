from __future__ import annotations

import math
import random
import sys
from dataclasses import replace

import pytest

from pak_simulator.model import Defect, Effect, Pak
from pak_simulator.simulation.planner import prepare_session, roll_defects
from pak_simulator.values import Span

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("pass_rate", [0.0, 1.0])
def test_forced_outcome_matches_measurement_limits(pak: Pak, pass_rate: float) -> None:
    check = replace(pak.profile.checks[0], low=10, high=20, value=Span(0, 30))
    profile = replace(pak.profile, checks=(check,), pass_rate=pass_rate)

    _, steps = prepare_session(profile, random.Random(1))

    assert steps[0].passed == bool(pass_rate) and check.within_limits(steps[0].value) == bool(pass_rate)


def test_transient_defect_is_rolled_again_on_retest(pak: Pak) -> None:
    defect = Defect("transient", 1, 0, {"test": Effect(passed=False)}, transient=True)
    profile = replace(pak.profile, defects=(defect,), pass_rate=None)

    defects = roll_defects(profile, random.Random(1), frozenset())

    assert defects == frozenset({"transient"})


def test_persistent_defect_disappears_when_repaired(pak: Pak) -> None:
    defect = Defect("fault", 1, 0, {"test": Effect(passed=False)})
    profile = replace(pak.profile, defects=(defect,), pass_rate=None)

    defects = roll_defects(profile, random.Random(1), frozenset({"fault"}))

    assert not defects


def test_failed_session_prefers_defined_defect(pak: Pak) -> None:
    defect = Defect(
        "fault",
        0.01,
        1,
        {"test": Effect(value=Span(-10, -10), name="fault", label="Fault", time=Span(1, 1), passed=False)},
    )
    profile = replace(pak.profile, defects=(defect,), pass_rate=0)

    defects, steps = prepare_session(profile, random.Random(1))

    assert defects == frozenset({"fault"}) and steps[0].value == -10


@pytest.mark.parametrize(
    "low, high",
    [
        (1e20, None),
        (None, 1e20),
        (-sys.float_info.max, 10.0),
        (None, sys.float_info.max),
        (-sys.float_info.max, sys.float_info.max),
    ],
)
def test_forced_failure_at_extreme_limits_is_consistent(pak: Pak, low: float | None, high: float | None) -> None:
    healthy_value = low if low is not None else high
    assert healthy_value is not None
    check = replace(pak.profile.checks[0], low=low, high=high, value=Span(healthy_value, healthy_value))
    profile = replace(pak.profile, checks=(check,), pass_rate=0)

    _, steps = prepare_session(profile, random.Random(1))
    step = steps[0]

    assert not step.passed and check.within_limits(step.value) is False
    assert step.value is None or math.isfinite(step.value)
