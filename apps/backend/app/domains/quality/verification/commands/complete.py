from datetime import UTC, datetime
from uuid import UUID

from ..contracts import VerificationPakPort
from ..exceptions import VerificationSessionIncompleteError, VerificationSessionNotRunningError
from ..model import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)
from ..queries import required_session
from ..repository import VerificationRepository
from ..rules import ensure_session_owned_by_pak


async def abort_running_step(
    repository: VerificationRepository, step: VerificationStep, *, completed_at: datetime
) -> VerificationStep:
    return await repository.finish_step(
        step,
        status=VerificationStepStatus.ABORTED,
        measurement_value=step.measurement_value,
        measurement_min_value=step.measurement_min_value,
        measurement_max_value=step.measurement_max_value,
        measurement_unit=step.measurement_unit,
        completed_at=completed_at,
    )


async def close_incomplete(
    repository: VerificationRepository, item: VerificationSession, *, completed_at: datetime
) -> None:
    if item.status != VerificationSessionStatus.RUNNING:
        return
    running_step = await repository.get_running_step(item.id)
    if running_step is not None:
        await abort_running_step(repository, running_step, completed_at=completed_at)
    await repository.finish_session(
        item, status=VerificationSessionStatus.INCOMPLETE, completed_at=completed_at
    )


class CompleteVerificationSession:
    def __init__(self, repository: VerificationRepository) -> None:
        self._repository = repository

    async def execute(
        self, *, pak: VerificationPakPort, session_id: UUID, status: VerificationSessionStatus
    ) -> VerificationSession:
        if status not in {
            VerificationSessionStatus.PASSED,
            VerificationSessionStatus.FAILED,
            VerificationSessionStatus.ABORTED,
        }:
            raise ValueError(
                "PAK may complete a session only with PASSED, FAILED or ABORTED status"
            )
        item = await required_session(self._repository, session_id)
        now = datetime.now(UTC)
        ensure_session_owned_by_pak(item, pak)
        if item.status != VerificationSessionStatus.RUNNING:
            if item.status == status:
                return item
            raise VerificationSessionNotRunningError
        running_step = await self._repository.get_running_step(item.id)
        if running_step is not None:
            if status != VerificationSessionStatus.ABORTED:
                raise VerificationSessionIncompleteError
            await abort_running_step(self._repository, running_step, completed_at=now)
        if (
            status == VerificationSessionStatus.PASSED
            and await self._repository.count_steps(
                session_id=item.id, status=VerificationStepStatus.PASSED
            )
            != item.total_steps
        ):
            raise VerificationSessionIncompleteError
        return await self._repository.finish_session(item, status=status, completed_at=now)
