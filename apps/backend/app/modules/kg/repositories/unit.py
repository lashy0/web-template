from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KgStatus, KgUnit


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
                short_id=(f"{short_code}-{dev_eui[-6:]}"),
                batch_id=batch_id,
                status=KgStatus.REGISTERED,
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

    async def list_by_batch(
        self,
        batch_id: UUID,
        *,
        for_update: bool = False,
    ) -> list[KgUnit]:
        statement = select(KgUnit).where(KgUnit.batch_id == batch_id).order_by(KgUnit.dev_eui.asc())

        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)

        result = await self._session.execute(statement)

        return list(result.scalars())

    async def update_status(
        self,
        kg: KgUnit,
        *,
        status: KgStatus,
    ) -> KgUnit:
        kg.status = status

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
        status: KgStatus | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[KgUnit], int]:
        filters: list[ColumnElement[bool]] = []

        if q:
            pattern = f"%{q.strip().lower()}%"

            filters.append(
                or_(
                    KgUnit.dev_eui.ilike(pattern),
                    KgUnit.short_id.ilike(pattern),
                )
            )

        if batch_id is not None:
            filters.append(KgUnit.batch_id == batch_id)

        if status is not None:
            filters.append(KgUnit.status == status)

        statement = select(KgUnit).where(*filters)

        column = {
            "dev_eui": KgUnit.dev_eui,
            "batch_id": KgUnit.batch_id,
            "status": KgUnit.status,
            "created_at": KgUnit.created_at,
            "updated_at": KgUnit.updated_at,
        }[sort]

        sorted_column = column.desc() if order == "desc" else column.asc()
        statement = statement.order_by(sorted_column, KgUnit.dev_eui.asc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        count = await self._session.scalar(select(func.count()).select_from(KgUnit).where(*filters))
        result = await self._session.execute(statement)

        return list(result.scalars()), int(count or 0)

    async def has_non_registered_by_batch(self, batch_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        KgUnit.batch_id == batch_id,
                        KgUnit.status != KgStatus.REGISTERED,
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

        statement = select(KgUnit).where(KgUnit.dev_eui.in_(dev_euis)).order_by(KgUnit.dev_eui)

        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)

        result = await self._session.scalars(statement)

        return list(result)

    async def update_status_many(
        self,
        kg_units: Sequence[KgUnit],
        *,
        status: KgStatus,
    ) -> None:
        for kg in kg_units:
            kg.status = status

        await self._session.flush()

    async def get_max_dev_eui_by_prefix(self, prefix: str) -> str | None:
        result: str | None = await self._session.scalar(
            select(func.max(KgUnit.dev_eui)).where(KgUnit.dev_eui.like(f"{prefix}%"))
        )

        return result

    async def lock_dev_eui_allocation(self, prefix: str) -> None:
        await self._session.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"kg-dev-eui:{prefix}")))
        )
