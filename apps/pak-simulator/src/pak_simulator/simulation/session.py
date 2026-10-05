"""Execute one verification attempt and own the server sessions of each slot."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

import httpx2

from pak_simulator.contracts import SessionResponse, SessionResult, VerificationClient
from pak_simulator.errors import ApiError, ClientError, error_message
from pak_simulator.model import PlannedStep, Profile, Sessions
from pak_simulator.simulation.planner import prepare_session
from pak_simulator.simulation.state import AttemptOutcome, SlotState, SlotStatus, Unit

Sleep = Callable[[float], Awaitable[None]]

logger = logging.getLogger(__name__)


class SessionExecutor:
    def __init__(
        self,
        client: VerificationClient,
        profile: Profile,
        sessions: Sessions,
        *,
        speed: float,
        sleep: Sleep,
        on_cleanup_error: Callable[[str], None],
        access_denied: Callable[[], bool],
    ) -> None:
        self._client = client
        self._profile = profile
        self._sessions = sessions
        self._speed = speed
        self._sleep = sleep
        self._on_cleanup_error = on_cleanup_error
        self._access_denied = access_denied
        self._open_sessions: dict[int, str] = {}

    @property
    def open_sessions(self) -> int:
        return len(self._open_sessions)

    async def execute(self, slot: SlotState, unit: Unit, rng: random.Random) -> AttemptOutcome:
        unit.defects, steps = prepare_session(self._profile, rng, unit.defects)
        unit.attempt += 1
        slot.begin(unit, len(steps))
        abandon_at = None

        if len(steps) > 1 and rng.random() < self._sessions.abandon:
            abandon_at = rng.randint(2, len(steps))

        session = await self._open(slot.no, unit, len(steps))
        try:
            return await self._execute_plan(slot, unit, session.id, steps, abandon_at)
        except ApiError as exc:
            if not exc.unauthorized:
                await self._abort_if_allowed(slot.no)

            raise
        except asyncio.CancelledError:
            note = "PAK stopped after an access error" if self._access_denied() else "Simulator stopped"
            slot.end(SlotStatus.ABORTED, note)
            try:
                await self._abort_if_allowed(slot.no)
            except Exception:
                logger.exception("Session cleanup failed during cancellation for slot %s", slot.no)

            raise
        except BaseException:
            # Cleanup also runs on process-level interrupts.
            await self._abort_if_allowed(slot.no)
            raise

    async def _execute_plan(
        self,
        slot: SlotState,
        unit: Unit,
        session_id: str,
        steps: list[PlannedStep],
        abandon_at: int | None,
    ) -> AttemptOutcome:
        try:
            outcome = await self._execute_steps(slot, session_id, steps, abandon_at)
        except ApiError as exc:
            # Zero completed steps can still mean an incompatible first step is
            # running. Restart once without regenerating the plan or attempt.
            if exc.status != 409 or exc.code != "verification_step_already_exists" or slot.outcomes:
                raise

            await self._complete(slot.no, session_id, "aborted")
            session = await self._open(slot.no, unit, len(steps))
            session_id = session.id
            outcome = await self._execute_steps(slot, session_id, steps, abandon_at)

        if outcome is not AttemptOutcome.ABANDONED:
            await self._complete(
                slot.no,
                session_id,
                "passed" if outcome is AttemptOutcome.PASSED else "failed",
            )

        return outcome

    async def _execute_steps(
        self,
        slot: SlotState,
        session_id: str,
        steps: list[PlannedStep],
        abandon_at: int | None,
    ) -> AttemptOutcome:
        for step in steps:
            if step.no == abandon_at:
                # Opening the next unit closes this session as incomplete.
                return AttemptOutcome.ABANDONED

            slot.step_started(step)
            await self._client.start_step(
                session_id, step_no=step.no, name=step.name, label=step.label, group=step.group
            )
            await self._sleep(step.duration / self._speed)
            await self._client.complete_step(
                session_id,
                step_no=step.no,
                passed=step.passed,
                value=step.value,
                low=step.low,
                high=step.high,
                unit=step.unit,
            )
            slot.step_completed(step)

            if not step.passed and step.critical:
                break

        return AttemptOutcome.FAILED if slot.failed_labels else AttemptOutcome.PASSED

    async def _abort_if_allowed(self, slot_no: int) -> None:
        session_id = self._open_sessions.get(slot_no)

        if session_id is not None and not self._access_denied():
            await self._abort(slot_no, session_id)

    async def _open(self, slot_no: int, unit: Unit, total_steps: int) -> SessionResponse:
        session = await self._open_session(slot_no, unit, total_steps)

        if (
            session.completed_steps
            or session.firmware_version != self._profile.firmware_version
            or session.total_steps != total_steps
        ):
            await self._complete(slot_no, session.id, "aborted")
            session = await self._open_session(slot_no, unit, total_steps)

        return session

    async def _open_session(self, slot_no: int, unit: Unit, total_steps: int) -> SessionResponse:
        session = await self._client.open_session(
            dev_eui=unit.dev_eui,
            slot_no=slot_no,
            firmware_version=self._profile.firmware_version,
            total_steps=total_steps,
        )
        # A confirmed new session supersedes the old session in this slot.
        self._open_sessions[slot_no] = session.id

        return session

    async def _complete(self, slot_no: int, session_id: str, result: SessionResult) -> None:
        await self._client.complete_session(session_id, result)
        self._open_sessions.pop(slot_no, None)

    async def _abort(self, slot_no: int, session_id: str) -> None:
        try:
            await asyncio.wait_for(self._complete(slot_no, session_id, "aborted"), 15.0)
        except (ApiError, ClientError, httpx2.TransportError, TimeoutError) as exc:
            self._on_cleanup_error(
                f"Could not abort session {session_id}: {error_message(exc)} Backend will expire it when stale."
            )

            return

    async def close(self) -> None:
        """Abort at most one currently open session per slot."""
        results = await asyncio.gather(
            *(self._abort(slot_no, session_id) for slot_no, session_id in tuple(self._open_sessions.items())),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, BaseException)]

        if failures:
            raise BaseExceptionGroup("Session cleanup failed", failures)
