from datetime import UTC, datetime
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.quality.defects.repository import DefectGroupRepository
from app.contexts.quality.tests.commands import ObservePakTest
from app.contexts.quality.tests.repository import PakTestRepository

from ..contracts import VerificationPakPort
from ..exceptions import (
    VerificationStepAlreadyCompletedError,
    VerificationStepAlreadyExistsError,
    VerificationStepInProgressError,
    VerificationStepNotFoundError,
)
from ..model import VerificationStep, VerificationStepStatus
from ..queries import required_session
from ..repository import VerificationRepository
from ..rules import (
    ensure_session_owned_by_pak,
    ensure_session_running,
    ensure_step_in_range,
    same_step_result,
)


class StartVerificationStep:
    def __init__(self, repository: VerificationRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self,
        *,
        pak: VerificationPakPort,
        session_id: UUID,
        step_no: int,
        test_name: str,
        test_label: str,
        error_group_code: str,
    ) -> VerificationStep:
        item = await required_session(self._repository, session_id)
        now = datetime.now(UTC)
        ensure_session_owned_by_pak(item, pak)
        ensure_session_running(item)
        ensure_step_in_range(item, step_no)
        existing = await self._repository.get_step(session_id=item.id, step_no=step_no)
        if existing is not None:
            if (
                existing.test_name == test_name
                and existing.test_label == test_label
                and existing.error_group_code == error_group_code
            ):
                await self._repository.touch_session(item, at=now)
                return existing
            raise VerificationStepAlreadyExistsError
        if await self._repository.has_running_step(item.id):
            raise VerificationStepInProgressError
        pak_test = await ObservePakTest(
            DefectGroupRepository(self._repository.session),
            PakTestRepository(self._repository.session),
            self._audit,
        ).execute(
            pak=pak,
            test_name=test_name,
            test_label=test_label,
            defect_group_code=error_group_code,
            seen_at=now,
        )
        step = await self._repository.create_step(
            session_id=item.id,
            step_no=step_no,
            pak_test_id=pak_test.id,
            defect_group_id=pak_test.defect_group_id,
            test_name=test_name,
            test_label=test_label,
            error_group_code=error_group_code,
        )
        await self._repository.touch_session(item, at=now)
        return step


class CompleteVerificationStep:
    def __init__(self, repository: VerificationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        pak: VerificationPakPort,
        session_id: UUID,
        step_no: int,
        status: VerificationStepStatus,
        measurement_value: float | None,
        measurement_min_value: float | None,
        measurement_max_value: float | None,
        measurement_unit: str | None,
    ) -> VerificationStep:
        if status not in {VerificationStepStatus.PASSED, VerificationStepStatus.FAILED}:
            raise ValueError("PAK may complete a step only with PASSED or FAILED status")
        item = await required_session(self._repository, session_id)
        now = datetime.now(UTC)
        ensure_session_owned_by_pak(item, pak)
        ensure_session_running(item)
        ensure_step_in_range(item, step_no)
        step = await self._repository.get_step(session_id=item.id, step_no=step_no, for_update=True)
        if step is None:
            raise VerificationStepNotFoundError
        if step.status != VerificationStepStatus.RUNNING:
            if same_step_result(
                step,
                status=status,
                measurement_value=measurement_value,
                measurement_min_value=measurement_min_value,
                measurement_max_value=measurement_max_value,
                measurement_unit=measurement_unit,
            ):
                await self._repository.touch_session(item, at=now)
                return step
            raise VerificationStepAlreadyCompletedError
        step = await self._repository.finish_step(
            step,
            status=status,
            measurement_value=measurement_value,
            measurement_min_value=measurement_min_value,
            measurement_max_value=measurement_max_value,
            measurement_unit=measurement_unit,
            completed_at=now,
        )
        await self._repository.touch_session(item, at=now)
        return step
