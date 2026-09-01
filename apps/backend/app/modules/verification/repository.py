from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.kg.models import KgUnit
from app.modules.verification.models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)


class VerificationSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        kg_dev_eui: str,
        pak_id: UUID,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> VerificationSession:
        verification_session = VerificationSession(
            kg_dev_eui=kg_dev_eui,
            pak_id=pak_id,
            slot_no=slot_no,
            firmware_version=firmware_version,
            total_steps=total_steps,
            status=VerificationSessionStatus.RUNNING,
        )

        self._session.add(verification_session)

        await self._session.flush()
        await self._session.refresh(verification_session)

        return verification_session

    async def get_by_id(self, session_id: UUID) -> VerificationSession | None:
        return await self._session.get(VerificationSession, session_id)

    async def get_by_id_for_update(self, session_id: UUID) -> VerificationSession | None:
        result = await self._session.execute(
            select(VerificationSession)
            .where(
                VerificationSession.id == session_id
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def get_running_by_kg(self, kg_dev_eui: str) -> VerificationSession | None:
        result = await self._session.execute(
            select(VerificationSession)
            .where(
                VerificationSession.kg_dev_eui == kg_dev_eui,
                VerificationSession.status == VerificationSessionStatus.RUNNING,
            )
        )

        return result.scalar_one_or_none()

    async def get_running_by_pak_slot(
        self,
        *,
        pak_id: UUID,
        slot_no: int,
    ) -> VerificationSession | None:
        result = await self._session.execute(
            select(VerificationSession)
            .where(
                VerificationSession.pak_id == pak_id,
                VerificationSession.slot_no == slot_no,
                VerificationSession.status == VerificationSessionStatus.RUNNING,
            )
        )

        return result.scalar_one_or_none()

    async def complete(
        self,
        verification_session: VerificationSession,
        *,
        status: VerificationSessionStatus,
        completed_at: datetime,
    ) -> VerificationSession:
        verification_session.status = status
        verification_session.completed_at = completed_at
        verification_session.last_activity_at = completed_at

        await self._session.flush()
        await self._session.refresh(verification_session)

        return verification_session

    async def search(
        self,
        *,
        q: str | None,
        pak_id: UUID | None,
        status: VerificationSessionStatus | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[VerificationSession], int]:
        filters: list[ColumnElement[bool]] = []

        if q:
            pattern = f"%{q.strip().lower()}%"

            filters.append(VerificationSession.kg_dev_eui.ilike(pattern))

        if pak_id is not None:
            filters.append(VerificationSession.pak_id == pak_id)

        if status is not None:
            filters.append(VerificationSession.status == status)

        statement = select(VerificationSession).where(*filters)

        column = {
            "kg_dev_eui": VerificationSession.kg_dev_eui,
            "status": VerificationSession.status,
            "started_at": VerificationSession.started_at,
            "completed_at": VerificationSession.completed_at,
            "created_at": VerificationSession.created_at,
            "updated_at": VerificationSession.updated_at,
        }[sort]

        sorted_column = (
            column.desc().nulls_last()
            if order == "desc"
            else column.asc().nulls_last()
        )

        statement = (
            statement
            .order_by(
                sorted_column,
                VerificationSession.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count = await self._session.scalar(
            select(func.count())
            .select_from(VerificationSession)
            .where(*filters)
        )

        result = await self._session.execute(statement)

        return list(result.scalars()), int(count or 0)

    async def touch_activity(
        self,
        verification_session: VerificationSession,
        *,
        at: datetime,
    ) -> VerificationSession:
        verification_session.last_activity_at = at

        await self._session.flush()
        await self._session.refresh(
            verification_session
        )

        return verification_session

    async def list_stale_running_for_update(
        self,
        *,
        cutoff: datetime,
        limit: int = 100,
    ) -> list[VerificationSession]:
        result = await self._session.scalars(
            select(VerificationSession)
            .where(
                VerificationSession.status == VerificationSessionStatus.RUNNING,
                VerificationSession.last_activity_at <= cutoff,
            )
            .order_by(VerificationSession.last_activity_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        return list(result)

    async def exists_by_pak_id(self, pak_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        VerificationSession.pak_id == pak_id
                    )
                )
            )
        )

    async def exists_by_kg_dev_eui(self, kg_dev_eui: str) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        VerificationSession.kg_dev_eui == kg_dev_eui
                    )
                )
            )
        )

    async def exists_by_batch_id(
        self,
        batch_id: UUID,
    ) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        VerificationSession.kg_dev_eui == KgUnit.dev_eui,
                        KgUnit.batch_id == batch_id,
                    )
                )
            )
        )

    async def lock_session_open(
        self,
        *,
        kg_dev_eui: str,
        pak_id: UUID,
        slot_no: int,
    ) -> None:
        keys = (
            f"verification:kg:{kg_dev_eui}",
            (
                "verification:pak-slot:"
                f"{pak_id}:{slot_no}"
            ),
        )

        for key in keys:
            await self._session.execute(
                select(
                    func.pg_advisory_xact_lock(
                        func.hashtext(key)
                    )
                )
            )


class VerificationStepRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        session_id: UUID,
        step_no: int,
        test_name: str,
        test_label: str | None,
    ) -> VerificationStep:
        step = VerificationStep(
            session_id=session_id,
            step_no=step_no,
            test_name=test_name,
            test_label=test_label,
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
            select(VerificationStep)
            .where(
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
        )

        return result.scalar_one_or_none()

    async def list_by_session(
        self,
        session_id: UUID,
    ) -> list[VerificationStep]:
        result = await self._session.scalars(
            select(VerificationStep)
            .where(
                VerificationStep.session_id == session_id
            )
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
        error_group_code: str | None,
        completed_at: datetime,
    ) -> VerificationStep:
        step.status = status

        step.measurement_value = measurement_value
        step.measurement_min_value = measurement_min_value
        step.measurement_max_value = measurement_max_value
        step.measurement_unit = measurement_unit

        step.error_group_code = error_group_code

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
