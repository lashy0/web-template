from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pak_simulator.simulation.statistics import RunStats

pytestmark = pytest.mark.unit


def test_statistics_snapshot_preserves_counts_and_cannot_be_changed() -> None:
    stats = RunStats(
        passed=2,
        failed=1,
        abandoned=4,
        skipped=3,
        errors=1,
        cleanup_errors=5,
        internal_errors=2,
    )
    snapshot = stats.snapshot()

    assert snapshot.completed_attempts == 3 and snapshot.execution_errors == 8
    assert snapshot.attempts_processed == 11 and snapshot.verifiable_attempts == 8
    assert snapshot.actual_pass_rate == pytest.approx(2 / 3)

    stats.record_passed()
    stats.record_cleanup_error()
    stats.record_internal_error()

    assert stats.completed_attempts == 4 and stats.execution_errors == 10
    assert stats.attempts_processed == 12 and stats.verifiable_attempts == 9
    assert stats.actual_pass_rate == 0.75
    assert snapshot.completed_attempts == 3 and snapshot.execution_errors == 8
    assert snapshot.actual_pass_rate == pytest.approx(2 / 3)

    with pytest.raises(FrozenInstanceError):
        snapshot.passed = 99  # type: ignore[misc]
