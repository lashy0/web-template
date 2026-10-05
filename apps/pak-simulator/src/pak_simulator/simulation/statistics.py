"""Typed attempt counts and immutable statistics snapshots."""

from __future__ import annotations

from dataclasses import dataclass


class _StatsTotals:
    """Derived counts shared by mutable statistics and immutable snapshots."""

    __slots__ = ()

    passed: int
    failed: int
    abandoned: int
    skipped: int
    errors: int
    cleanup_errors: int
    internal_errors: int

    @property
    def completed_attempts(self) -> int:
        return self.passed + self.failed

    @property
    def execution_errors(self) -> int:
        return self.errors + self.cleanup_errors + self.internal_errors

    @property
    def attempts_processed(self) -> int:
        """Attempt results, excluding cleanup and PAK-level internal errors."""
        return self.passed + self.failed + self.abandoned + self.skipped + self.errors

    @property
    def actual_pass_rate(self) -> float | None:
        completed = self.passed + self.failed
        return self.passed / completed if completed else None

    @property
    def verifiable_attempts(self) -> int:
        """Attempts other than skips, cleanup errors and PAK-level internal errors."""
        return self.passed + self.failed + self.abandoned + self.errors


@dataclass(slots=True)
class RunStats(_StatsTotals):
    """Mutable counts collected while a PAK run is active."""

    passed: int = 0
    failed: int = 0
    abandoned: int = 0
    skipped: int = 0
    errors: int = 0
    cleanup_errors: int = 0
    internal_errors: int = 0

    def record_passed(self) -> None:
        self.passed += 1

    def record_failed(self) -> None:
        self.failed += 1

    def record_abandoned(self) -> None:
        self.abandoned += 1

    def record_skipped(self) -> None:
        self.skipped += 1

    def record_error(self) -> None:
        self.errors += 1

    def record_cleanup_error(self) -> None:
        self.cleanup_errors += 1

    def record_internal_error(self) -> None:
        self.internal_errors += 1

    def snapshot(self) -> RunStatsSnapshot:
        """Copy current counts into an immutable value."""
        return RunStatsSnapshot(
            passed=self.passed,
            failed=self.failed,
            abandoned=self.abandoned,
            skipped=self.skipped,
            errors=self.errors,
            cleanup_errors=self.cleanup_errors,
            internal_errors=self.internal_errors,
        )


@dataclass(frozen=True, slots=True)
class RunStatsSnapshot(_StatsTotals):
    """Immutable attempt counts for a live or completed run."""

    passed: int = 0
    failed: int = 0
    abandoned: int = 0
    skipped: int = 0
    errors: int = 0
    cleanup_errors: int = 0
    internal_errors: int = 0
