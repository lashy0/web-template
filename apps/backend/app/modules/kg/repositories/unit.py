from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, and_, case, delete, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from app.modules.verification.models import VerificationSession, VerificationSessionStatus

from ..models import KgState, KgUnit, LoRaWanCredentials
from ..schemas.state import KgCurrentState
from ..schemas.unit import KgBatchListItem


@dataclass(frozen=True, slots=True)
class KgListItem:
    kg: KgUnit
    current_state: KgCurrentState


class KgRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_many(
        self,
        *,
        dev_euis: Sequence[str],
        short_code: str,
        batch_id: UUID,
    ) -> list[KgUnit]:
        kg_units = [
            KgUnit(
                dev_eui=dev_eui,
                short_id=f"{short_code}-{dev_eui[-6:]}",
                batch_id=batch_id,
                state=KgState.REGISTERED,
            )
            for dev_eui in dev_euis
        ]

        if not kg_units:
            return []

        self._session.add_all(kg_units)
        await self._session.flush()

        return kg_units

    async def get_by_dev_eui(
        self,
        dev_eui: str,
        *,
        for_update: bool = False,
    ) -> KgUnit | None:
        return await self._session.get(
            KgUnit,
            dev_eui,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_with_current_state(self, dev_eui: str) -> KgListItem | None:
        latest_session = self._latest_session_rank()
        current_state = self._current_state_expression(latest_session)

        result = await self._session.execute(
            select(KgUnit, current_state)
            .outerjoin(
                latest_session,
                and_(
                    latest_session.c.rank == 1,
                    KgUnit.dev_eui == latest_session.c.kg_dev_eui,
                ),
            )
            .where(KgUnit.dev_eui == dev_eui)
        )
        row = result.tuples().one_or_none()

        return None if row is None else KgListItem(kg=row[0], current_state=KgCurrentState(row[1]))

    async def list_by_batch(
        self,
        batch_id: UUID,
        *,
        for_update: bool = False,
    ) -> list[KgUnit]:
        statement = select(KgUnit).where(
            KgUnit.batch_id == batch_id,
        ).order_by(KgUnit.dev_eui.asc())

        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)

        result = await self._session.execute(statement)

        return list(result.scalars())

    async def list_batch_items(
        self,
        batch_id: UUID,
        *,
        page: int,
        page_size: int,
        q: str | None,
        current_state: KgCurrentState | None,
    ) -> tuple[list[KgBatchListItem], int]:
        filters: list[ColumnElement[bool]] = [KgUnit.batch_id == batch_id]

        if q:
            filters.append(KgUnit.dev_eui.ilike(f"%{q.strip()}%"))

        latest_session = self._latest_session_rank()
        computed_state = self._current_state_expression(latest_session)

        if current_state is not None:
            filters.append(computed_state == current_state)

        statement = (
            select(
                KgUnit.dev_eui,
                computed_state,
                VerificationSession.firmware_version,
                VerificationSession.started_at,
                func.count().over().label("total"),
            )
            .outerjoin(
                latest_session,
                and_(
                    latest_session.c.rank == 1,
                    KgUnit.dev_eui == latest_session.c.kg_dev_eui,
                ),
            )
            .outerjoin(
                VerificationSession,
                VerificationSession.id == latest_session.c.id,
            )
            .where(*filters)
            .order_by(KgUnit.dev_eui.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(statement)
        rows = list(result.tuples())

        return (
            [
                KgBatchListItem(
                    dev_eui=dev_eui,
                    current_state=KgCurrentState(value),
                    firmware_version=firmware_version,
                    last_verification_at=last_verification_at,
                )
                for dev_eui, value, firmware_version, last_verification_at, _ in rows
            ],
            rows[0][4] if rows else 0,
        )

    async def list_without_credentials_by_batch(
        self,
        batch_id: UUID,
        *,
        limit: int,
    ) -> list[KgUnit]:
        statement = (
            select(KgUnit)
            .outerjoin(
                LoRaWanCredentials,
                LoRaWanCredentials.kg_dev_eui == KgUnit.dev_eui,
            )
            .where(
                KgUnit.batch_id == batch_id,
                LoRaWanCredentials.kg_dev_eui.is_(None),
            )
            .order_by(KgUnit.dev_eui.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)

        return list(result.scalars())

    async def update_state(
        self,
        kg: KgUnit,
        *,
        state: KgState,
    ) -> KgUnit:
        kg.state = state

        await self._session.flush()
        await self._session.refresh(kg)

        return kg

    async def delete(self, kg: KgUnit) -> None:
        await self._session.delete(kg)
        await self._session.flush()

    async def delete_by_batch(self, batch_id: UUID) -> None:
        await self._session.execute(delete(KgUnit).where(KgUnit.batch_id == batch_id))

    async def search(
        self,
        *,
        q: str | None,
        batch_id: UUID | None,
        current_state: KgCurrentState | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[KgListItem], int]:
        filters: list[ColumnElement[bool]] = []

        if q:
            pattern = f"%{q.strip().lower()}%"
            filters.append(or_(
                KgUnit.dev_eui.ilike(pattern),
                KgUnit.short_id.ilike(pattern),
            ))

        if batch_id is not None:
            filters.append(KgUnit.batch_id == batch_id)

        latest_session = self._latest_session_rank()
        computed_state = self._current_state_expression(latest_session)

        if current_state is not None:
            filters.append(computed_state == current_state)

        column = {
            "dev_eui": KgUnit.dev_eui,
            "batch_id": KgUnit.batch_id,
            "current_state": computed_state,
            "created_at": KgUnit.created_at,
            "updated_at": KgUnit.updated_at,
        }[sort]

        sorted_column = column.desc() if order == "desc" else column.asc()

        statement = (
            select(
                KgUnit,
                computed_state,
                func.count().over().label("total"),
            )
            .outerjoin(
                latest_session,
                and_(
                    latest_session.c.rank == 1,
                    KgUnit.dev_eui == latest_session.c.kg_dev_eui,
                ),
            )
            .where(*filters)
            .order_by(sorted_column, KgUnit.dev_eui.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(statement)
        rows = list(result.tuples())

        return (
            [KgListItem(kg=kg, current_state=KgCurrentState(value)) for kg, value, _ in rows],
            rows[0][2] if rows else 0,
        )

    async def has_non_registered_by_batch(self, batch_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        KgUnit.batch_id == batch_id,
                        KgUnit.state != KgState.REGISTERED,
                    )
                )
            )
        )

    async def get_many_by_dev_euis(
        self,
        dev_euis: Sequence[str],
        *,
        for_update: bool = False,
    ) -> list[KgUnit]:
        if not dev_euis:
            return []

        statement = select(KgUnit).where(
            KgUnit.dev_eui.in_(dev_euis),
        ).order_by(KgUnit.dev_eui)

        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)

        result = await self._session.scalars(statement)

        return list(result)

    async def get_max_dev_eui_by_prefix(self, prefix: str) -> str | None:
        result: str | None = await self._session.scalar(
            select(
                func.max(KgUnit.dev_eui),
            ).where(KgUnit.dev_eui.like(f"{prefix}%"))
        )

        return result

    async def lock_dev_eui_allocation(self, prefix: str) -> None:
        await self._session.execute(
            select(
                func.pg_advisory_xact_lock(func.hashtext(f"kg-dev-eui:{prefix}")),
            )
        )

    @staticmethod
    def _latest_session_rank() -> Subquery:
        return select(
            VerificationSession.id.label("id"),
            VerificationSession.kg_dev_eui.label("kg_dev_eui"),
            VerificationSession.status.label("status"),
            func.row_number()
            .over(
                partition_by=VerificationSession.kg_dev_eui,
                order_by=(
                    VerificationSession.started_at.desc(),
                    VerificationSession.id.desc(),
                ),
            )
            .label("rank"),
        ).subquery()

    @staticmethod
    def _current_state_expression(latest_session: Subquery) -> ColumnElement[str]:
        return case(
            (
                KgUnit.state == KgState.SCRAPPED,
                literal(KgCurrentState.SCRAPPED.value),
            ),
            (
                latest_session.c.status == VerificationSessionStatus.RUNNING,
                literal(KgCurrentState.ON_OTK.value),
            ),
            (
                latest_session.c.status == VerificationSessionStatus.PASSED,
                literal(KgCurrentState.OTK_PASSED.value),
            ),
            (
                latest_session.c.status.in_(
                    [VerificationSessionStatus.FAILED, VerificationSessionStatus.ABORTED]
                ),
                literal(KgCurrentState.OTK_FAILED.value),
            ),
            else_=literal(KgCurrentState.REGISTERED.value),
        )
