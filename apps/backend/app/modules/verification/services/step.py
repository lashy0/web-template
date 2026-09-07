from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pak.models import PakDevice
from app.modules.pak.services import PakTestCatalogService

from ..exceptions import (
    VerificationStepAlreadyCompletedError,
    VerificationStepAlreadyExistsError,
    VerificationStepInProgressError,
    VerificationStepNotFoundError,
)
from ..models import VerificationStep, VerificationStepStatus
from ..repositories import (
    VerificationSessionRepository,
    VerificationStepRepository,
)
from . import lifecycle
from .queries import required_session_for_update


class VerificationStepService:
    """Step execution in the caller-owned transaction."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        catalog: PakTestCatalogService,
    ) -> None:
        self._session = session
        self._pak_test_catalog = catalog

    async def start_step(
        self,
        *,
        pak: PakDevice,
        session_id: UUID,
        step_no: int,
        test_name: str,
        test_label: str,
        error_group_code: str,
    ) -> VerificationStep:
        now = datetime.now(UTC)

        session = self._session
        verification_repository = VerificationSessionRepository(session)
        step_repository = VerificationStepRepository(session)

        verification_session = await required_session_for_update(
            verification_repository,
            session_id,
        )
        now = datetime.now(UTC)

        lifecycle.ensure_session_owned_by_pak(verification_session, pak)
        lifecycle.ensure_session_running(verification_session)
        lifecycle.ensure_step_in_range(verification_session, step_no)

        existing = await step_repository.get_by_session_and_step_no(
            session_id=verification_session.id,
            step_no=step_no,
        )

        if existing is not None:
            if (
                existing.test_name == test_name
                and existing.test_label == test_label
                and existing.error_group_code == error_group_code
            ):
                # Safe retry of the same start request
                await verification_repository.touch_activity(
                    verification_session,
                    at=now,
                )

                return existing

            raise VerificationStepAlreadyExistsError

        if await step_repository.exists_running_by_session(verification_session.id):
            raise VerificationStepInProgressError

        pak_test = await self._pak_test_catalog.observe_in_session(
            session,
            pak=pak,
            test_name=test_name,
            test_label=test_label,
            defect_group_code=error_group_code,
            seen_at=now,
        )

        step = await step_repository.create(
            session_id=verification_session.id,
            step_no=step_no,
            pak_test_id=pak_test.id,
            defect_group_id=pak_test.defect_group_id,
            test_name=test_name,
            test_label=test_label,
            error_group_code=error_group_code,
        )

        await verification_repository.touch_activity(
            verification_session,
            at=now,
        )

        return step

    async def complete_step(
        self,
        *,
        pak: PakDevice,
        session_id: UUID,
        step_no: int,
        status: VerificationStepStatus,
        measurement_value: float | None,
        measurement_min_value: float | None,
        measurement_max_value: float | None,
        measurement_unit: str | None,
    ) -> VerificationStep:
        if status not in {
            VerificationStepStatus.PASSED,
            VerificationStepStatus.FAILED,
        }:
            raise ValueError("PAK may complete a step only with PASSED or FAILED status")

        now = datetime.now(UTC)

        session = self._session
        verification_repository = VerificationSessionRepository(session)
        step_repository = VerificationStepRepository(session)

        verification_session = await required_session_for_update(
            verification_repository,
            session_id,
        )
        now = datetime.now(UTC)

        lifecycle.ensure_session_owned_by_pak(verification_session, pak)
        lifecycle.ensure_session_running(verification_session)
        lifecycle.ensure_step_in_range(verification_session, step_no)

        step = await step_repository.get_by_session_and_step_no_for_update(
            session_id=verification_session.id,
            step_no=step_no,
        )

        if step is None:
            raise VerificationStepNotFoundError

        if step.status != VerificationStepStatus.RUNNING:
            if lifecycle.same_step_result(
                step,
                status=status,
                measurement_value=measurement_value,
                measurement_min_value=measurement_min_value,
                measurement_max_value=measurement_max_value,
                measurement_unit=measurement_unit,
            ):
                # Response may have been lost and PAK repeated the same request
                await verification_repository.touch_activity(
                    verification_session,
                    at=now,
                )

                return step

            raise VerificationStepAlreadyCompletedError

        step = await step_repository.complete(
            step,
            status=status,
            measurement_value=measurement_value,
            measurement_min_value=measurement_min_value,
            measurement_max_value=measurement_max_value,
            measurement_unit=measurement_unit,
            completed_at=now,
        )

        await verification_repository.touch_activity(
            verification_session,
            at=now,
        )

        return step
