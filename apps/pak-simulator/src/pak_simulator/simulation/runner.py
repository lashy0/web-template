"""Schedule and run verification sessions on PAK slots."""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum, auto

import httpx2

from pak_simulator.contracts import VerificationClient
from pak_simulator.errors import ApiError, ClientError, error_message
from pak_simulator.model import Pak, Sessions
from pak_simulator.simulation.queue import UnitQueue
from pak_simulator.simulation.randomness import RandomStreams
from pak_simulator.simulation.reporting import AttemptReporter
from pak_simulator.simulation.retests import RetestDecision, RetestPolicy
from pak_simulator.simulation.session import SessionExecutor, Sleep
from pak_simulator.simulation.state import (
    AttemptOutcome,
    Clock,
    EventLog,
    EventSinkError,
    PakSnapshot,
    PakStatus,
    RunResult,
    SlotSnapshot,
    SlotState,
    SlotStatus,
    Unit,
)
from pak_simulator.simulation.statistics import RunStats

_UNAVAILABLE_UNITS = frozenset(
    {
        "verification_kg_not_found",
        "verification_kg_scrapped",
        "verification_kg_packed",
        "verification_batch_archived",
    }
)
"""Units the server will never let this PAK verify; they leave the pool."""

_ERROR_PAUSE = 10.0
"""Real seconds a slot waits after an error before taking the next unit."""

logger = logging.getLogger(__name__)


class _PakAccessDenied(Exception):
    """Stop this PAK's task group after a persistent authentication or access error."""


class _StopReason(Enum):
    ACCESS_DENIED = auto()
    INTERNAL_ERROR = auto()
    OUTPUT_ERROR = auto()
    CANCELLED = auto()
    EXECUTION_ERRORS = auto()


class PakRun:
    """Run one PAK with independent slots or synchronized loads."""

    def __init__(
        self,
        pak: Pak,
        sessions: Sessions,
        client: VerificationClient,
        *,
        speed: float,
        loop: bool,
        seed: int,
        events: EventLog,
        sleep: Sleep = asyncio.sleep,
        clock: Clock = time.monotonic,
    ) -> None:
        self.pak = pak
        self.slots = [SlotState(no, clock=clock) for no in range(1, pak.slots + 1)]
        self.stats = RunStats()
        self._reporter = AttemptReporter(pak.code, events, self.stats)
        self.alert: str | None = None
        self.next_load_at: float | None = None
        self._sessions = sessions
        self._speed = speed
        self._loop = loop
        self._random = RandomStreams(seed, pak.code)
        self._schedule = {slot.no: self._random.schedule(slot.no) for slot in self.slots}
        self._load_rng = self._random.schedule(0)
        self._sleep = sleep
        self._clock = clock
        self._queue = UnitQueue(pak.dev_euis, loop=loop)
        self._queue_changed = asyncio.Event()
        self._retest_policy = RetestPolicy(sessions.retest, len(self.slots), self._random.retest)
        self._status = PakStatus.RUNNING
        self._stop_reason: _StopReason | None = None
        self._executor = SessionExecutor(
            client,
            pak.profile,
            sessions,
            speed=speed,
            sleep=sleep,
            on_cleanup_error=self._reporter.cleanup_error,
            access_denied=lambda: self._stop_reason is _StopReason.ACCESS_DENIED,
        )

    @property
    def status(self) -> PakStatus:
        if self._status is PakStatus.RUNNING and self.next_load_at is not None:
            return PakStatus.WAITING

        return self._status

    @property
    def next_load_in(self) -> float | None:
        """Real seconds until the next group of units is loaded."""
        if self.next_load_at is None:
            return None

        return max(0.0, self.next_load_at - self._clock())

    @property
    def queued_units(self) -> int:
        return self._queue.queued

    @property
    def looping(self) -> bool:
        return self._loop

    @property
    def processed_units(self) -> int:
        return self._queue.processed

    @property
    def running_units(self) -> int:
        return self._queue.running

    @property
    def waiting_units(self) -> int:
        """Include units reserved by slots that are waiting between sessions."""
        return self._queue.waiting

    @property
    def actual_pass_rate(self) -> float | None:
        return self.stats.actual_pass_rate

    @property
    def result(self) -> RunResult:
        return RunResult(
            self.pak.code,
            self.status,
            self.stats.completed_attempts,
            self.stats.failed,
            self.stats.abandoned,
            self.stats.skipped,
            self.stats.execution_errors,
            self.processed_units,
            self._queue.unfinished,
        )

    def snapshot(self) -> PakSnapshot:
        return PakSnapshot(
            self.pak.code,
            self.pak.profile.key,
            self.pak.profile.pass_rate,
            len(self.pak.dev_euis),
            self.status,
            tuple(SlotSnapshot.from_state(slot) for slot in self.slots),
            self.stats.snapshot(),
            self.alert,
            self.looping,
            self.processed_units,
            self.running_units,
            self.waiting_units,
            self.queued_units,
            self.next_load_in,
            self.actual_pass_rate,
        )

    async def run(self) -> RunResult:
        """Contain internal PAK failures while preserving global output errors and cancellation."""
        try:
            return await self._run()
        except* EventSinkError:
            self._stop(_StopReason.OUTPUT_ERROR)
            raise
        except* Exception as exc:
            self._internal_error(exc)

        return self.result

    async def _run(self) -> RunResult:
        try:
            await self._run_slots()
        except asyncio.CancelledError:
            self._stop(_StopReason.CANCELLED)
            raise
        except Exception:
            self._status = PakStatus.ERROR
            raise
        finally:
            await self._close_sessions()

        return self._finish()

    async def _run_slots(self) -> None:
        try:
            if self._sessions.together:
                await self._serve_loads()
            else:
                async with asyncio.TaskGroup() as group:
                    for slot in self.slots:
                        group.create_task(self._serve(slot))
        except* _PakAccessDenied:
            # The access-error handler has already stopped and reported this PAK.
            pass

    async def _close_sessions(self) -> None:
        # Also closes an interrupted final session when --once has no
        # next unit to make the backend close it as incomplete.
        try:
            await self._executor.close()
        except Exception:
            if self._stop_reason is not _StopReason.CANCELLED:
                raise
            # Cleanup failure must not replace the user's cancellation.
            logger.exception("Session cleanup failed while stopping PAK %s", self.pak.code)

    def _stop(self, reason: _StopReason) -> None:
        self._stop_reason = reason
        self._status = PakStatus.STOPPED if reason is _StopReason.CANCELLED else PakStatus.ERROR

    def _internal_error(self, exc: BaseException) -> None:
        self._stop(_StopReason.INTERNAL_ERROR)
        self.stats.record_internal_error()
        self.alert = "PAK stopped after an internal simulator error. See the diagnostic traceback."

        for slot in self.slots:
            if slot.status in (SlotStatus.WAITING, SlotStatus.RUNNING, SlotStatus.ABORTED):
                slot.end(SlotStatus.ABORTED, "PAK stopped after an internal simulator error")

            slot.next_session_at = None

        self.next_load_at = None
        logger.error("Internal simulator error for PAK %s", self.pak.code, exc_info=exc)
        self._reporter.log(None, self.alert, "error", result=SlotStatus.ERROR)

    def _finish(self) -> RunResult:
        if self._stop_reason is _StopReason.ACCESS_DENIED:
            self._reporter.log(
                None,
                "PAK stopped after an access error. Remaining units were not processed.",
                "error",
            )

            return self.result

        if self.stats.execution_errors:
            self._stop(_StopReason.EXECUTION_ERRORS)
            self._reporter.log(None, "PAK finished with execution errors", "error")

            return self.result

        self._status = PakStatus.FINISHED
        self._reporter.log(None, "All units processed for this PAK", "info")

        return self.result

    async def _serve(self, slot: SlotState) -> None:
        """Serve one slot on its own: the next unit goes in as soon as it is free."""
        await self._pause(self._sessions.start.sample(self._schedule[slot.no]))
        delay = 0.0

        while True:
            # Clear before checking the queue, with no await until waiting,
            # so a notification cannot be lost between the check and wait.
            self._queue_changed.clear()
            unit = self._take_unit(slot.no)

            if unit is None:
                can_retest = self._sessions.retest.chance > 0 and self._sessions.retest.max_attempts > 1

                if self._queue.should_wait(can_retest=can_retest):
                    await self._queue_changed.wait()
                    continue

                self._done(slot)

                return

            try:
                if delay:
                    # Reserve the next unit while this slot waits, including in loop mode.
                    slot.next_session_at = self._clock() + delay
                    try:
                        await self._sleep(delay)
                    finally:
                        slot.next_session_at = None

                outcome = await self._attempt(slot, unit)
            except (asyncio.CancelledError, Exception):
                self._return_unit(slot, unit)
                raise

            if outcome is AttemptOutcome.SKIPPED:
                delay = 0.2
            elif outcome is AttemptOutcome.ERROR:
                delay = _ERROR_PAUSE
            else:
                decision = self._retest_decision(slot, unit) if outcome is AttemptOutcome.FAILED else None
                pause = self._sessions.retest.pause if decision and decision.in_place else self._sessions.swap
                delay = pause.sample(self._schedule[slot.no]) / self._speed

    async def _serve_loads(self) -> None:
        """Load every slot, wait until all have finished, then load the next units."""
        while True:
            async with asyncio.TaskGroup() as group:
                loads = [group.create_task(self._serve_load(slot)) for slot in self.slots]

            if not any(load.result() for load in loads):
                return

            if not self.queued_units:
                for slot in self.slots:
                    self._done(slot)
                return

            pause = self._sessions.swap.sample(self._load_rng)
            self.next_load_at = self._clock() + pause / self._speed
            self._reporter.log(
                None,
                f"Waiting between loads: {pause / self._speed:.1f} s",
                "info",
            )
            try:
                await self._pause(pause)
            finally:
                self.next_load_at = None

    async def _serve_load(self, slot: SlotState) -> bool:
        """Verify a unit in the slot, retesting it there while it fails; ``False`` when no unit is left."""
        await self._pause(self._sessions.start.sample(self._schedule[slot.no]))

        while (unit := self._take_unit(slot.no)) is not None:
            try:
                outcome = await self._attempt(slot, unit)

                if outcome is AttemptOutcome.SKIPPED:
                    await self._sleep(0.2)
                    continue

                while outcome is AttemptOutcome.FAILED and self._retest_policy.decide(
                    unit, slot.no, same_slot_only=True
                ):
                    self._queue.reserve_retest(unit)
                    try:
                        await self._pause(self._sessions.retest.pause.sample(self._schedule[slot.no]))
                        outcome = await self._attempt(slot, unit)
                    finally:
                        self._queue.release(unit)

                if outcome is AttemptOutcome.ERROR:
                    await self._sleep(_ERROR_PAUSE)
            except (asyncio.CancelledError, Exception):
                self._return_unit(slot, unit)
                raise

            return True

        self._done(slot)

        return False

    async def _attempt(self, slot: SlotState, unit: Unit) -> AttemptOutcome:
        """Verify the unit once and report its attempt outcome."""
        if self._status is PakStatus.ERROR:
            raise _PakAccessDenied

        self._queue.start(unit)

        try:
            try:
                outcome = await self._executor.execute(slot, unit, self._random.session(unit))
            except ApiError as exc:
                if exc.code in _UNAVAILABLE_UNITS or exc.code == "verification_session_already_running":
                    self._skip(slot, unit, exc)
                    outcome = AttemptOutcome.SKIPPED
                else:
                    raise
            else:
                self.alert = None
                note = "The operator took the unit out" if outcome is AttemptOutcome.ABANDONED else ""
                self._reporter.finished(slot, unit, outcome, note)
        except ApiError as exc:
            outcome = self._on_api_error(slot, exc)
        except (ClientError, httpx2.TransportError) as exc:
            outcome = self._reporter.execution_error(slot, error_message(exc))
        finally:
            self._queue.release(unit)
            self._queue_changed.set()

        self._queue.finish(unit, error=outcome is AttemptOutcome.ERROR)

        return outcome

    def _done(self, slot: SlotState) -> None:
        slot.end(SlotStatus.DONE, "No units left")

        if not self.stats.verifiable_attempts:
            self.alert = "None of the units can be verified"

    def _take_unit(self, slot_no: int) -> Unit | None:
        return None if self._status is PakStatus.ERROR else self._queue.take(slot_no)

    def _return_unit(self, slot: SlotState, unit: Unit) -> None:
        """Keep an interrupted or reserved unit queued when this PAK stops."""
        if slot.status is SlotStatus.RUNNING:
            note = "PAK stopped after an access error" if self._status is PakStatus.ERROR else "Simulator stopped"
            slot.end(SlotStatus.ABORTED, note)

        self._queue.return_unit(unit)
        self._queue_changed.set()

    def _retest_decision(self, slot: SlotState, unit: Unit) -> RetestDecision | None:
        """Choose and queue the seeded retry route for an independent slot."""
        decision = self._retest_policy.decide(unit, slot.no)

        if decision is not None:
            self._queue.retest(unit, only_slot=decision.only_slot, avoid_slot=decision.avoid_slot)
            self._queue_changed.set()

        return decision

    def _skip(self, slot: SlotState, unit: Unit, exc: ApiError) -> None:
        if exc.code in _UNAVAILABLE_UNITS:
            self._queue.exclude(unit.dev_eui)

        self._reporter.skipped(slot, unit, exc)

    def _on_api_error(self, slot: SlotState, exc: ApiError) -> AttemptOutcome:
        if not exc.unauthorized:
            return self._reporter.execution_error(slot, error_message(exc))

        alert = error_message(exc)
        self._stop(_StopReason.ACCESS_DENIED)
        announce = alert != self.alert

        if announce:
            self.alert = alert

        self._reporter.access_error(slot, alert, announce=announce)

        raise _PakAccessDenied from exc

    async def _pause(self, seconds: float) -> None:
        await self._sleep(seconds / self._speed)
