from __future__ import annotations

import builtins
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.kg.services import KgService
from app.modules.pak.models import PakDevice

from ..exceptions import (
    VerificationKgNotFoundError,
    VerificationSessionAlreadyRunningError,
    VerificationSessionIncompleteError,
    VerificationSessionNotRunningError,
)
from ..models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)
from ..repositories import (
    VerificationSessionRepository,
    VerificationStepRepository,
)
from . import lifecycle
from .queries import required_session_for_update


class VerificationSessionService:
    """Session lifecycle in the caller-owned transaction."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        reopen_inactivity: timedelta = timedelta(minutes=60),
    ) -> None:
        self._session = session
        self._reopen_inactivity = reopen_inactivity

    @staticmethod
    async def has_pak_history(session: AsyncSession, pak_id: UUID) -> bool:
        return await VerificationSessionRepository(session).exists_by_pak_id(pak_id)

    @staticmethod
    async def has_batch_history(session: AsyncSession, batch_id: UUID) -> bool:
        """Query history in the caller's transaction without opening another session."""
        return await VerificationSessionRepository(session).exists_by_batch_id(batch_id)

    async def get(self, session_id: UUID) -> VerificationSession | None:
        session = self._session
        return await VerificationSessionRepository(session).get_by_id(session_id)

    async def get_detail(
        self, session_id: UUID
    ) -> (
        tuple[
            VerificationSession,
            builtins.list[VerificationStep],
        ]
        | None
    ):
        session = self._session
        verification_session = await VerificationSessionRepository(session).get_by_id(session_id)

        if verification_session is None:
            return None

        steps = await VerificationStepRepository(session).list_by_session(verification_session.id)

        return verification_session, steps

    async def list(
        self,
        *,
        q: str | None,
        pak_id: UUID | None,
        status: VerificationSessionStatus | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[builtins.list[VerificationSession], int]:
        session = self._session

        return await VerificationSessionRepository(session).search(
            q=q,
            pak_id=pak_id,
            status=status,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def open_session(
        self,
        *,
        pak: PakDevice,
        kg_dev_eui: str,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> VerificationSession:
        now = datetime.now(UTC)

        session = self._session
        verification_repository = VerificationSessionRepository(session)
        step_repository = VerificationStepRepository(session)
        kg_service = KgService(session)

        await verification_repository.lock_session_open(
            kg_dev_eui=kg_dev_eui,
            pak_id=pak.id,
            slot_no=slot_no,
        )

        candidates = await verification_repository.lock_running_candidates(
            kg_dev_eui=kg_dev_eui, pak_id=pak.id, slot_no=slot_no
        )
        await kg_service.lock_for_update([kg_dev_eui, *(item.kg_dev_eui for item in candidates)])
        now = datetime.now(UTC)

        kg = await kg_service.get(kg_dev_eui)

        if kg is None:
            raise VerificationKgNotFoundError

        running_by_kg = await verification_repository.get_running_by_kg(kg.dev_eui)

        if running_by_kg is not None:
            same_location = running_by_kg.pak_id == pak.id and running_by_kg.slot_no == slot_no

            if lifecycle.is_reopen_stale(
                running_by_kg, now=now, reopen_inactivity=self._reopen_inactivity
            ):
                await self.close_incomplete(
                    verification_repository,
                    step_repository,
                    kg_service,
                    running_by_kg,
                    completed_at=now,
                )

            elif same_location:
                # Idempotent open retry
                await verification_repository.touch_activity(
                    running_by_kg,
                    at=now,
                )

                return running_by_kg

            else:
                # The same KG is actively being tested somewhere else
                raise VerificationSessionAlreadyRunningError

        # Re-read after a stale KG session may have been closed above
        running_by_slot = await verification_repository.get_running_by_pak_slot(
            pak_id=pak.id,
            slot_no=slot_no,
        )

        if running_by_slot is not None:
            # A new KG appearing in the same physical
            # slot means the previous run was not completed correctly
            await self.close_incomplete(
                verification_repository,
                step_repository,
                kg_service,
                running_by_slot,
                completed_at=now,
            )

        kg = await kg_service.begin_verification(kg.dev_eui)

        verification_session = await verification_repository.create(
            kg_dev_eui=kg.dev_eui,
            pak_id=pak.id,
            slot_no=slot_no,
            firmware_version=firmware_version,
            total_steps=total_steps,
        )

        return verification_session

    async def complete_session(
        self,
        *,
        pak: PakDevice,
        session_id: UUID,
        status: VerificationSessionStatus,
    ) -> VerificationSession:
        if status not in {
            VerificationSessionStatus.PASSED,
            VerificationSessionStatus.FAILED,
            VerificationSessionStatus.ABORTED,
        }:
            raise ValueError(
                "PAK may complete a session only with PASSED, FAILED or ABORTED status"
            )

        now = datetime.now(UTC)

        session = self._session
        verification_repository = VerificationSessionRepository(session)
        step_repository = VerificationStepRepository(session)
        kg_service = KgService(session)

        verification_session = await required_session_for_update(
            verification_repository,
            session_id,
        )
        now = datetime.now(UTC)

        lifecycle.ensure_session_owned_by_pak(verification_session, pak)

        if verification_session.status != VerificationSessionStatus.RUNNING:
            if verification_session.status == status:
                # Idempotent completion retry
                return verification_session

            raise VerificationSessionNotRunningError

        running_step = await step_repository.get_running_by_session_for_update(
            verification_session.id
        )

        if running_step is not None:
            if status != VerificationSessionStatus.ABORTED:
                raise VerificationSessionIncompleteError

            await self._abort_step(
                step_repository,
                running_step,
                completed_at=now,
            )

        if status == VerificationSessionStatus.PASSED:
            passed_steps = await step_repository.count_by_session_and_status(
                session_id=verification_session.id, status=VerificationStepStatus.PASSED
            )

            if passed_steps != verification_session.total_steps:
                raise VerificationSessionIncompleteError

        await kg_service.finish_verification(
            verification_session.kg_dev_eui, status=lifecycle.kg_status_after_completion(status)
        )

        verification_session = await verification_repository.complete(
            verification_session,
            status=status,
            completed_at=now,
        )

        return verification_session

    async def close_incomplete(
        self,
        verification_repository: VerificationSessionRepository,
        step_repository: VerificationStepRepository,
        kg_service: KgService,
        verification_session: VerificationSession,
        *,
        completed_at: datetime,
    ) -> None:
        if verification_session.status != VerificationSessionStatus.RUNNING:
            return

        running_step = await step_repository.get_running_by_session_for_update(
            verification_session.id
        )

        if running_step is not None:
            await self._abort_step(
                step_repository,
                running_step,
                completed_at=completed_at,
            )

        await verification_repository.complete(
            verification_session,
            status=VerificationSessionStatus.INCOMPLETE,
            completed_at=completed_at,
        )

        await kg_service.release_incomplete_verification(verification_session.kg_dev_eui)

    @staticmethod
    async def _abort_step(
        repository: VerificationStepRepository,
        step: VerificationStep,
        *,
        completed_at: datetime,
    ) -> VerificationStep:
        return await repository.complete(
            step,
            status=VerificationStepStatus.ABORTED,
            measurement_value=step.measurement_value,
            measurement_min_value=step.measurement_min_value,
            measurement_max_value=step.measurement_max_value,
            measurement_unit=step.measurement_unit,
            completed_at=completed_at,
        )
