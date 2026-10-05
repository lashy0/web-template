from __future__ import annotations

import pytest

from pak_simulator.simulation.queue import UnitQueue
from pak_simulator.simulation.state import Unit

pytestmark = pytest.mark.unit

DEV_EUI = "0000000000000001"


def test_loop_reserves_unit_before_session_starts() -> None:
    queue = UnitQueue((DEV_EUI,), loop=True)
    queue.take(1)

    assert queue.take(2) is None


def test_interrupted_unit_returns_to_queue() -> None:
    queue = UnitQueue((DEV_EUI,), loop=False)
    unit = queue.take(1)
    assert unit is not None

    queue.return_unit(unit)

    assert queue.take(1) is unit


def test_retest_cannot_return_to_avoided_slot() -> None:
    queue = UnitQueue((), loop=False)
    queue.retest(Unit(DEV_EUI), only_slot=None, avoid_slot=1)

    assert queue.take(1) is None and queue.take(2) is not None


def test_retest_stays_in_assigned_slot() -> None:
    queue = UnitQueue((), loop=False)
    unit = Unit(DEV_EUI)
    queue.retest(unit, only_slot=1, avoid_slot=None)

    assert queue.take(2) is None and queue.take(1) is unit


@pytest.mark.parametrize("loop", [False, True])
def test_progress_tracks_reservations_retests_errors_and_cancellation(loop: bool) -> None:
    queue = UnitQueue((DEV_EUI, "0000000000000002"), loop=loop)
    assert (queue.waiting, queue.running, queue.processed, queue.unfinished) == (2, 0, 0, 2)
    first, second = queue.take(1), queue.take(2)
    assert first is not None and second is not None
    assert queue.waiting == 2  # Reservations remain waiting until a session starts.
    queue.start(first)
    queue.start(second)
    assert (queue.waiting, queue.running) == (0, 2)
    queue.finish(first, error=True)
    assert (queue.waiting, queue.processed, queue.unfinished) == (int(loop), 1, 2)
    queue.retest(first, only_slot=1, avoid_slot=None)
    assert (queue.waiting, queue.processed, queue.unfinished) == (1, 0, 2)
    retry = queue.take(1)
    assert retry is first
    queue.start(retry)
    assert queue.waiting == 0
    queue.finish(retry, error=False)
    queue.return_unit(second)
    assert (queue.waiting, queue.running, queue.processed, queue.unfinished) == (1 + int(loop), 0, 1, 1)


@pytest.mark.parametrize("loop", [False, True])
def test_in_place_retest_stays_waiting_until_started(loop: bool) -> None:
    queue = UnitQueue((DEV_EUI,), loop=loop)
    unit = queue.take(1)
    assert unit is not None
    queue.start(unit)
    queue.finish(unit, error=False)
    queue.reserve_retest(unit)
    assert (queue.waiting, queue.running, queue.processed) == (1, 0, 0)
    queue.start(unit)
    assert queue.waiting == 0
    queue.finish(unit, error=False)
    assert queue.waiting == int(loop) and queue.unfinished == 0


def test_loop_counts_units_after_exclusion_and_repeated_cycles() -> None:
    queue = UnitQueue((DEV_EUI,), loop=True)
    unit = queue.take(1)
    assert unit is not None
    queue.start(unit)
    queue.finish(unit, error=False)
    repeated = queue.take(1)
    assert repeated is not None and repeated.cycle == unit.cycle + 1
    queue.start(repeated)
    assert (queue.waiting, queue.running, queue.processed) == (0, 1, 1)
    queue.exclude(DEV_EUI)
    queue.release(repeated)
    assert (queue.waiting, queue.queued) == (0, 0)
    assert queue.take(2) is None
    queue.retest(repeated, only_slot=1, avoid_slot=None)
    assert queue.waiting == 1
    retry = queue.take(1)
    assert retry is repeated and queue.waiting == 1
    queue.start(retry)
    assert queue.waiting == 0
    queue.finish(retry, error=False)
    assert queue.waiting == 0
