from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import VerificationStep, VerificationStepStatus


class VerificationStepRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        session_id: UUID,
        step_no: int,
        pak_test_id: UUID,
        defect_group_id: UUID,
        test_name: str,
        test_label: str,
        error_group_code: str,
    ) -> VerificationStep:
        step = VerificationStep(
            session_id=session_id,
            step_no=step_no,
            pak_test_id=pak_test_id,
            defect_group_id=defect_group_id,
            test_name=test_name,
            test_label=test_label,
            error_group_code=error_group_code,
            status=VerificationStepStatus.RUNNING,
        )

        self._session.add(step)

        await self._session.flush()
        await self._session.refresh(step)

        return step

    async def get_by_session_and_step_no(
        self,
        *,
        session_id: UUID,
        step_no: int,
    ) -> VerificationStep | None:
        result = await self._session.execute(
            select(VerificationStep).where(
                VerificationStep.session_id == session_id,
                VerificationStep.step_no == step_no,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_session_and_step_no_for_update(
        self,
        *,
        session_id: UUID,
        step_no: int,
    ) -> VerificationStep | None:
        result = await self._session.execute(
            select(VerificationStep)
            .where(
                VerificationStep.session_id == session_id,
                VerificationStep.step_no == step_no,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        return result.scalar_one_or_none()

    async def get_running_by_session_for_update(
        self,
        session_id: UUID,
    ) -> VerificationStep | None:
        result = await self._session.execute(
            select(VerificationStep)
            .where(
                VerificationStep.session_id == session_id,
                VerificationStep.status == VerificationStepStatus.RUNNING,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        return result.scalar_one_or_none()

    async def list_by_session(
        self,
        session_id: UUID,
    ) -> list[VerificationStep]:
        result = await self._session.scalars(
            select(VerificationStep)
            .where(VerificationStep.session_id == session_id)
            .order_by(VerificationStep.step_no.asc())
        )

        return list(result)

    async def complete(
        self,
        step: VerificationStep,
        *,
        status: VerificationStepStatus,
        measurement_value: float | None,
        measurement_min_value: float | None,
        measurement_max_value: float | None,
        measurement_unit: str | None,
        completed_at: datetime,
    ) -> VerificationStep:
        step.status = status
        step.measurement_value = measurement_value
        step.measurement_min_value = measurement_min_value
        step.measurement_max_value = measurement_max_value
        step.measurement_unit = measurement_unit
        step.completed_at = completed_at

        await self._session.flush()
        await self._session.refresh(step)

        return step

    async def count_by_session_and_status(
        self,
        *,
        session_id: UUID,
        status: VerificationStepStatus,
    ) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(VerificationStep)
            .where(
                VerificationStep.session_id == session_id,
                VerificationStep.status == status,
            )
        )

        return int(count or 0)

    async def exists_running_by_session(
        self,
        session_id: UUID,
    ) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        VerificationStep.session_id == session_id,
                        VerificationStep.status == VerificationStepStatus.RUNNING,
                    )
                )
            )
        )
