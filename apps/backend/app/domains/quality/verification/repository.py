from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.production.kg.model import KgUnit

from .model import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)


class VerificationRepository:
    """Verification persistence, PostgreSQL locks, and bulk history facts.

    The open path always obtains advisory locks in this exact order: KG then
    PAK slot. Row candidates and related KG rows are each ordered explicitly.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Expose the caller-owned UoW to quality-internal collaborators only."""
        return self._session

    async def lock_open_keys(self, *, kg_dev_eui: str, pak_id: UUID, slot_no: int) -> None:
        for key in (f"verification:kg:{kg_dev_eui}", f"verification:pak-slot:{pak_id}:{slot_no}"):
            await self._session.execute(select(func.pg_advisory_xact_lock(func.hashtext(key))))

    async def lock_running_candidates(
        self, *, kg_dev_eui: str, pak_id: UUID, slot_no: int
    ) -> list[VerificationSession]:
        result = await self._session.scalars(
            select(VerificationSession)
            .where(
                VerificationSession.status == VerificationSessionStatus.RUNNING,
                or_(
                    VerificationSession.kg_dev_eui == kg_dev_eui,
                    and_(
                        VerificationSession.pak_id == pak_id, VerificationSession.slot_no == slot_no
                    ),
                ),
            )
            .order_by(VerificationSession.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list(result)

    async def create_session(
        self,
        *,
        kg_dev_eui: str,
        pak_id: UUID,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> VerificationSession:
        item = VerificationSession(
            kg_dev_eui=kg_dev_eui,
            pak_id=pak_id,
            slot_no=slot_no,
            firmware_version=firmware_version,
            total_steps=total_steps,
            status=VerificationSessionStatus.RUNNING,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def get_session(
        self, session_id: UUID, *, for_update: bool = False
    ) -> VerificationSession | None:
        return await self._session.get(
            VerificationSession,
            session_id,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_running_by_kg(self, kg_dev_eui: str) -> VerificationSession | None:
        return (
            await self._session.execute(
                select(VerificationSession).where(
                    VerificationSession.kg_dev_eui == kg_dev_eui,
                    VerificationSession.status == VerificationSessionStatus.RUNNING,
                )
            )
        ).scalar_one_or_none()

    async def get_running_by_pak_slot(
        self, *, pak_id: UUID, slot_no: int
    ) -> VerificationSession | None:
        return (
            await self._session.execute(
                select(VerificationSession).where(
                    VerificationSession.pak_id == pak_id,
                    VerificationSession.slot_no == slot_no,
                    VerificationSession.status == VerificationSessionStatus.RUNNING,
                )
            )
        ).scalar_one_or_none()

    async def finish_session(
        self,
        item: VerificationSession,
        *,
        status: VerificationSessionStatus,
        completed_at: datetime,
    ) -> VerificationSession:
        item.status, item.completed_at, item.last_activity_at = status, completed_at, completed_at
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def touch_session(
        self, item: VerificationSession, *, at: datetime
    ) -> VerificationSession:
        item.last_activity_at = at
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def get_step(
        self, *, session_id: UUID, step_no: int, for_update: bool = False
    ) -> VerificationStep | None:
        statement = select(VerificationStep).where(
            VerificationStep.session_id == session_id, VerificationStep.step_no == step_no
        )
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_running_step(self, session_id: UUID) -> VerificationStep | None:
        return (
            await self._session.execute(
                select(VerificationStep)
                .where(
                    VerificationStep.session_id == session_id,
                    VerificationStep.status == VerificationStepStatus.RUNNING,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def create_step(
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
        item = VerificationStep(
            session_id=session_id,
            step_no=step_no,
            pak_test_id=pak_test_id,
            defect_group_id=defect_group_id,
            test_name=test_name,
            test_label=test_label,
            error_group_code=error_group_code,
            status=VerificationStepStatus.RUNNING,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def finish_step(
        self,
        item: VerificationStep,
        *,
        status: VerificationStepStatus,
        measurement_value: float | None,
        measurement_min_value: float | None,
        measurement_max_value: float | None,
        measurement_unit: str | None,
        completed_at: datetime,
    ) -> VerificationStep:
        item.status = status
        item.measurement_value = measurement_value
        item.measurement_min_value = measurement_min_value
        item.measurement_max_value = measurement_max_value
        item.measurement_unit = measurement_unit
        item.completed_at = completed_at
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def count_steps(self, *, session_id: UUID, status: VerificationStepStatus) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(VerificationStep)
                .where(VerificationStep.session_id == session_id, VerificationStep.status == status)
            )
            or 0
        )

    async def has_running_step(self, session_id: UUID) -> bool:
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

    async def list_steps(self, session_id: UUID) -> list[VerificationStep]:
        return list(
            await self._session.scalars(
                select(VerificationStep)
                .where(VerificationStep.session_id == session_id)
                .order_by(VerificationStep.step_no.asc())
            )
        )

    async def search_sessions(
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
            filters.append(VerificationSession.kg_dev_eui.ilike(f"%{q.strip().lower()}%"))
        if pak_id is not None:
            filters.append(VerificationSession.pak_id == pak_id)
        if status is not None:
            filters.append(VerificationSession.status == status)
        column = getattr(VerificationSession, sort)
        ordered = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        items = list(
            (
                await self._session.scalars(
                    select(VerificationSession)
                    .where(*filters)
                    .order_by(ordered, VerificationSession.id.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        count = await self._session.scalar(
            select(func.count()).select_from(VerificationSession).where(*filters)
        )
        return items, int(count or 0)

    async def claim_stale_running(
        self, *, cutoff: datetime, limit: int
    ) -> list[VerificationSession]:
        """Claim stale sessions atomically; concurrent sweepers skip claimed rows."""
        return list(
            await self._session.scalars(
                select(VerificationSession)
                .where(
                    VerificationSession.status == VerificationSessionStatus.RUNNING,
                    VerificationSession.last_activity_at <= cutoff,
                )
                .order_by(VerificationSession.last_activity_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
        )

    async def has_history_for_pak(self, pak_id: UUID) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(VerificationSession.pak_id == pak_id)))
        )

    async def has_history_for_kg(self, dev_eui: str) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(VerificationSession.kg_dev_eui == dev_eui))
            )
        )

    async def has_history_for_batch(self, batch_id: UUID) -> bool:
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
