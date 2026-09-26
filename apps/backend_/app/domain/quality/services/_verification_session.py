from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.db.enums import (
    KgOtkStatus,
    KgState,
    PakDeviceKind,
    VerificationSessionStatus,
    VerificationStepStatus,
)
from app.domain.quality.exceptions import (
    VerificationBatchArchivedError,
    VerificationKgNotFoundError,
    VerificationKgPackedError,
    VerificationKgScrappedError,
    VerificationSessionAlreadyRunningError,
    VerificationSessionIncompleteError,
    VerificationSessionNotFoundError,
    VerificationSessionNotRunningError,
    VerificationStepAlreadyCompletedError,
    VerificationStepAlreadyExistsError,
    VerificationStepInProgressError,
    VerificationStepNotFoundError,
    VerificationStepOutOfRangeError,
)

if TYPE_CHECKING:
    from app.domain.quality import schemas as s
    from app.domain.quality.services._pak_check import CheckObservation, PakCheckService

_OTK_STATUS_BY_RESULT = {
    VerificationSessionStatus.PASSED: KgOtkStatus.PASSED,
    VerificationSessionStatus.FAILED: KgOtkStatus.FAILED,
}


class VerificationSessionService(service.SQLAlchemyAsyncRepositoryService[m.VerificationSession]):
    """Verification sessions reported by PAKs.

    Row locks are always taken in the order batch, KG unit, PAK, session, so
    concurrent reports cannot deadlock each other.
    """

    class Repo(repository.SQLAlchemyAsyncRepository[m.VerificationSession]):
        """Verification session SQLAlchemy repository."""

        model_type = m.VerificationSession

    repository_type = Repo

    async def get_with_steps(self, session_id: UUID) -> m.VerificationSession:
        return await self.get(session_id, load=[selectinload(m.VerificationSession.steps)])

    async def open_session(
        self,
        pak: m.PakDevice,
        data: s.VerificationSessionOpen,
        *,
        reopen_inactivity: timedelta,
    ) -> m.VerificationSession:
        """Start a session for the KG unit in the PAK slot.

        The session already running for the unit in the same slot is resumed.
        A unit's session in another slot blocks it until that session has been
        idle for ``reopen_inactivity``; then it is closed as incomplete. A
        session still running in the slot for another unit is closed too: the
        PAK has moved on.
        """
        kg = await self._lock_verifiable_kg(data.dev_eui)

        # Packing is final; an engineering PAK may still examine a packed unit.
        if kg.state is KgState.PACKED and pak.kind is PakDeviceKind.OTK_LINE:
            raise VerificationKgPackedError

        await self._lock_pak(pak.id)
        now = datetime.now(UTC)

        by_kg: m.VerificationSession | None = None
        by_slot: m.VerificationSession | None = None

        for running in await self._lock_running_sessions(kg.dev_eui, pak_id=pak.id, slot_no=data.slot_no):
            if running.dev_eui == kg.dev_eui:
                by_kg = running
            else:
                by_slot = running

        if by_kg is not None:
            if now - by_kg.last_activity_at >= reopen_inactivity:
                await self._close_incomplete([by_kg], now=now)
            elif by_kg.pak_id == pak.id and by_kg.slot_no == data.slot_no:
                by_kg.last_activity_at = now
                await self.repository.session.flush()

                return by_kg
            else:
                raise VerificationSessionAlreadyRunningError

        if by_slot is not None:
            await self._close_incomplete([by_slot], now=now)

        item = m.VerificationSession(
            dev_eui=kg.dev_eui,
            batch_id=kg.batch_id,
            pak=pak,
            pak_kind=pak.kind,
            slot_no=data.slot_no,
            firmware_version=data.firmware_version,
            total_steps=data.total_steps,
            status=VerificationSessionStatus.RUNNING,
            started_at=now,
            last_activity_at=now,
        )
        self.repository.session.add(item)
        await self.repository.session.flush()

        return item

    async def start_step(
        self,
        pak: m.PakDevice,
        session_id: UUID,
        data: s.VerificationStepStart,
        *,
        checks: PakCheckService,
    ) -> tuple[m.VerificationStep, CheckObservation | None]:
        """Start a step and record its check in the catalog.

        Repeating a start with the same check returns the step without
        another observation.
        """
        item = await self._lock_running_session(pak, session_id)
        self._ensure_in_range(item, data.step_no)
        now = datetime.now(UTC)
        existing = await self._get_step(item.id, data.step_no)

        if existing is not None:
            if (existing.check_name, existing.check_label, existing.defect_group_code) != (
                data.check_name,
                data.check_label,
                data.defect_group_code,
            ):
                raise VerificationStepAlreadyExistsError

            item.last_activity_at = now
            await self.repository.session.flush()

            return existing, None

        running_step = select(m.VerificationStep.id).where(
            m.VerificationStep.session_id == item.id,
            m.VerificationStep.status == VerificationStepStatus.RUNNING,
        )

        if await self.repository.session.scalar(running_step) is not None:
            raise VerificationStepInProgressError

        observation = await checks.observe(
            pak=pak,
            name=data.check_name,
            label=data.check_label,
            defect_group_code=data.defect_group_code,
            seen_at=now,
        )
        step = m.VerificationStep(
            session_id=item.id,
            step_no=data.step_no,
            check_id=observation.check.id,
            check_name=data.check_name,
            check_label=data.check_label,
            defect_group_code=data.defect_group_code,
            defect_group_id=observation.check.defect_group_id,
            status=VerificationStepStatus.RUNNING,
            started_at=now,
        )
        self.repository.session.add(step)
        item.last_activity_at = now
        await self.repository.session.flush()

        return step, observation

    async def complete_step(
        self,
        pak: m.PakDevice,
        session_id: UUID,
        step_no: int,
        data: s.VerificationStepComplete,
    ) -> m.VerificationStep:
        """Record the result of a running step; repeating the same result returns the step."""
        item = await self._lock_running_session(pak, session_id)
        self._ensure_in_range(item, step_no)
        now = datetime.now(UTC)
        step = await self._get_step(item.id, step_no, for_update=True)

        if step is None:
            raise VerificationStepNotFoundError

        result = (
            VerificationStepStatus(data.status.value),
            data.measurement_value,
            data.measurement_min,
            data.measurement_max,
            data.measurement_unit,
        )

        if step.status is not VerificationStepStatus.RUNNING:
            if result != (
                step.status,
                step.measurement_value,
                step.measurement_min,
                step.measurement_max,
                step.measurement_unit,
            ):
                raise VerificationStepAlreadyCompletedError
        else:
            (
                step.status,
                step.measurement_value,
                step.measurement_min,
                step.measurement_max,
                step.measurement_unit,
            ) = result
            step.completed_at = now

        item.last_activity_at = now
        await self.repository.session.flush()

        return step

    async def complete_session(
        self,
        pak: m.PakDevice,
        session_id: UUID,
        data: s.VerificationSessionComplete,
    ) -> m.VerificationSession:
        """Finish the session with the PAK's result.

        A passed or failed session on an OTK-line PAK sets the OTK status of
        the KG unit. Repeating the same result returns the finished session,
        and so does aborting a session the system already closed as
        incomplete: both mean the PAK did not finish it.
        """
        status = VerificationSessionStatus(data.status.value)
        found = await self.repository.session.get(m.VerificationSession, session_id)

        if found is None or found.pak_id != pak.id:
            raise VerificationSessionNotFoundError

        # The KG unit is locked before the session, in the order sessions are opened.
        kg = await self._lock_kg(found.dev_eui)
        item = await self._lock_session(pak, session_id)

        if item.status is not VerificationSessionStatus.RUNNING:
            if item.status is status or (
                item.status is VerificationSessionStatus.INCOMPLETE
                and status is VerificationSessionStatus.ABORTED
            ):
                return item

            raise VerificationSessionNotRunningError

        now = datetime.now(UTC)
        running_step = await self.repository.session.scalar(
            select(m.VerificationStep)
            .where(
                m.VerificationStep.session_id == item.id,
                m.VerificationStep.status == VerificationStepStatus.RUNNING,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if running_step is not None:
            if status is not VerificationSessionStatus.ABORTED:
                raise VerificationSessionIncompleteError

            running_step.status = VerificationStepStatus.ABORTED
            running_step.completed_at = now

        if status is VerificationSessionStatus.PASSED:
            passed_steps = await self.repository.session.scalar(
                select(func.count()).where(
                    m.VerificationStep.session_id == item.id,
                    m.VerificationStep.status == VerificationStepStatus.PASSED,
                )
            )

            if passed_steps != item.total_steps:
                raise VerificationSessionIncompleteError

        item.status = status
        item.completed_at = now
        item.last_activity_at = now

        otk_status = _OTK_STATUS_BY_RESULT.get(status)

        if kg is not None and otk_status is not None and item.pak_kind is PakDeviceKind.OTK_LINE:
            kg.otk_status = otk_status
            kg.last_verification_at = now

        await self.repository.session.flush()

        return item

    async def expire_stale(self, *, idle_for: timedelta, limit: int) -> int:
        """Close up to ``limit`` running sessions idle for ``idle_for`` as incomplete.

        Sessions locked by a concurrent report are skipped until the next run.
        Returns the number of sessions closed.
        """
        now = datetime.now(UTC)
        stale = list(
            await self.repository.session.scalars(
                select(m.VerificationSession)
                .where(
                    m.VerificationSession.status == VerificationSessionStatus.RUNNING,
                    m.VerificationSession.last_activity_at <= now - idle_for,
                )
                .order_by(m.VerificationSession.last_activity_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
        )
        await self._close_incomplete(stale, now=now)

        return len(stale)

    async def _close_incomplete(
        self,
        sessions: list[m.VerificationSession],
        *,
        now: datetime,
    ) -> None:
        """Close sessions the PAK abandoned; ``last_activity_at`` keeps the PAK's last report."""
        if not sessions:
            return

        await self.repository.session.execute(
            update(m.VerificationStep)
            .where(
                m.VerificationStep.session_id.in_([item.id for item in sessions]),
                m.VerificationStep.status == VerificationStepStatus.RUNNING,
            )
            .values(status=VerificationStepStatus.ABORTED, completed_at=now)
        )

        for item in sessions:
            item.status = VerificationSessionStatus.INCOMPLETE
            item.completed_at = now

        await self.repository.session.flush()

    async def _lock_verifiable_kg(self, dev_eui: str) -> m.KgUnit:
        unit = await self.repository.session.get(m.KgUnit, dev_eui)

        if unit is None:
            raise VerificationKgNotFoundError

        # A shared lock keeps the batch from being archived before the session commits.
        batch: m.Batch | None = await self.repository.session.scalar(
            select(m.Batch)
            .where(m.Batch.id == unit.batch_id)
            .with_for_update(read=True, of=m.Batch)
            .execution_options(populate_existing=True)
        )
        kg = await self._lock_kg(dev_eui)

        if batch is None or kg is None:
            raise VerificationKgNotFoundError

        if batch.archived_at is not None:
            raise VerificationBatchArchivedError

        if kg.state is KgState.SCRAPPED:
            raise VerificationKgScrappedError

        return kg

    async def _lock_kg(self, dev_eui: str) -> m.KgUnit | None:
        kg: m.KgUnit | None = await self.repository.session.scalar(
            select(m.KgUnit)
            .where(m.KgUnit.dev_eui == dev_eui)
            .with_for_update(key_share=True, of=m.KgUnit)
            .execution_options(populate_existing=True)
        )

        return kg

    async def _lock_pak(self, pak_id: UUID) -> None:
        # Serializes the sessions opened on one PAK, so a slot never runs two.
        await self.repository.session.execute(
            select(m.PakDevice.id)
            .where(m.PakDevice.id == pak_id)
            .with_for_update(key_share=True)
        )

    async def _lock_running_sessions(
        self,
        dev_eui: str,
        *,
        pak_id: UUID,
        slot_no: int,
    ) -> list[m.VerificationSession]:
        return list(
            await self.repository.session.scalars(
                select(m.VerificationSession)
                .where(
                    m.VerificationSession.status == VerificationSessionStatus.RUNNING,
                    or_(
                        m.VerificationSession.dev_eui == dev_eui,
                        and_(
                            m.VerificationSession.pak_id == pak_id,
                            m.VerificationSession.slot_no == slot_no,
                        ),
                    ),
                )
                .order_by(m.VerificationSession.id)
                .with_for_update(of=m.VerificationSession)
                .execution_options(populate_existing=True)
            )
        )

    async def _lock_session(self, pak: m.PakDevice, session_id: UUID) -> m.VerificationSession:
        item = await self.get_one_or_none(
            m.VerificationSession.id == session_id,
            with_for_update=True,
            # A locked read must replace what an earlier read left in the session.
            execution_options={"populate_existing": True},
        )

        # Another PAK's session is reported as missing, not as forbidden.
        if item is None or item.pak_id != pak.id:
            raise VerificationSessionNotFoundError

        return item

    async def _lock_running_session(
        self,
        pak: m.PakDevice,
        session_id: UUID,
    ) -> m.VerificationSession:
        item = await self._lock_session(pak, session_id)

        if item.status is not VerificationSessionStatus.RUNNING:
            raise VerificationSessionNotRunningError

        return item

    async def _get_step(
        self,
        session_id: UUID,
        step_no: int,
        *,
        for_update: bool = False,
    ) -> m.VerificationStep | None:
        statement = select(m.VerificationStep).where(
            m.VerificationStep.session_id == session_id,
            m.VerificationStep.step_no == step_no,
        )

        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)

        step: m.VerificationStep | None = await self.repository.session.scalar(statement)

        return step

    @staticmethod
    def _ensure_in_range(item: m.VerificationSession, step_no: int) -> None:
        if step_no > item.total_steps:
            raise VerificationStepOutOfRangeError
