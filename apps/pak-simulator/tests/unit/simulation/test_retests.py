from __future__ import annotations

from dataclasses import replace

import pytest

from pak_simulator.model import Sessions
from pak_simulator.simulation.randomness import RandomStreams
from pak_simulator.simulation.retests import RetestDecision, RetestPolicy
from pak_simulator.simulation.state import Unit

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "other_slot, slot_count, same_slot_only, expected",
    [
        (0, 2, False, RetestDecision(only_slot=1, avoid_slot=None)),
        (1, 2, False, RetestDecision(only_slot=None, avoid_slot=1)),
        (1, 1, False, RetestDecision(only_slot=1, avoid_slot=None)),
        (1, 2, True, RetestDecision(only_slot=1, avoid_slot=None)),
    ],
)
def test_retest_placement_respects_routing_rules(
    sessions: Sessions,
    other_slot: float,
    slot_count: int,
    same_slot_only: bool,
    expected: RetestDecision,
) -> None:
    random = RandomStreams(4, "PAK")
    settings = replace(sessions.retest, chance=1, other_slot=other_slot, max_attempts=3)
    policy = RetestPolicy(settings, slot_count, random.retest)

    assert policy.decide(
        Unit("0000000000000001", attempt=1),
        failed_slot=1,
        same_slot_only=same_slot_only,
    ) == expected


def test_seeded_retest_placement_is_repeatable(sessions: Sessions) -> None:
    settings = replace(sessions.retest, chance=0.5, other_slot=0.5, max_attempts=3)
    dev_euis = tuple(f"{number:016X}" for number in range(1, 11))

    def decisions(order: tuple[str, ...]) -> dict[str, RetestDecision | None]:
        random = RandomStreams(4, "PAK")
        policy = RetestPolicy(settings, 2, random.retest)

        return {dev_eui: policy.decide(Unit(dev_eui, attempt=1), failed_slot=1) for dev_eui in order}

    expected = decisions(dev_euis)
    assert expected == decisions(dev_euis)
    assert expected == decisions(tuple(reversed(dev_euis)))


@pytest.mark.parametrize("chance, attempt", [(0, 1), (1, 2)])
def test_retest_policy_respects_attempt_limit_and_chance(
    sessions: Sessions,
    chance: float,
    attempt: int,
) -> None:
    random = RandomStreams(4, "PAK")
    policy = RetestPolicy(replace(sessions.retest, chance=chance, max_attempts=2), 2, random.retest)

    assert policy.decide(Unit("0000000000000001", attempt=attempt), failed_slot=1) is None
