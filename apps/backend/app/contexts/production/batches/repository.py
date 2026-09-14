from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import ORMOption

from app.components.keygen.types import ActivationType, LoRaWanVersion

from .model import Batch, BatchLoRaWanConfig, BatchStatus


class BatchRepository:
    """Batch persistence primitives. Transaction ownership stays with the caller."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _response_options() -> tuple[ORMOption, ...]:
        return (
            selectinload(Batch.production_order),
            selectinload(Batch.kg_version),
            selectinload(Batch.kg_dev_eui_prefix),
            selectinload(Batch.lorawan_config),
            selectinload(Batch.created_by_user),
        )

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
        created_by_user_id: UUID | None,
        activation_type: ActivationType,
        lorawan_version: LoRaWanVersion,
        join_eui: str,
        kg_version_id: UUID | None = None,
        production_order_id: UUID | None = None,
    ) -> Batch:
        batch = Batch(
            name=name,
            description=description,
            dev_eui_prefix=dev_eui_prefix,
            kg_version_id=kg_version_id,
            production_order_id=production_order_id,
            planned_qty=planned_qty,
            day_plan_qty=day_plan_qty,
            status=BatchStatus.IN_PRODUCTION,
            created_by_user_id=created_by_user_id,
            lorawan_config=BatchLoRaWanConfig(
                activation_type=activation_type,
                lorawan_version=lorawan_version,
                join_eui=join_eui,
            ),
        )
        self._session.add(batch)
        await self._session.flush()
        return await self.refresh_response(batch)

    async def get(self, batch_id: UUID, *, for_update: bool = False) -> Batch | None:
        return await self._session.get(  # type: ignore[no-any-return]
            Batch,
            batch_id,
            with_for_update=for_update,
            populate_existing=for_update,
            options=self._response_options(),
        )

    async def refresh_response(self, batch: Batch) -> Batch:
        await self._session.refresh(batch)
        await self._session.refresh(
            batch,
            attribute_names=[
                "kg_version",
                "kg_dev_eui_prefix",
                "production_order",
                "lorawan_config",
                "created_by_user",
            ],
        )
        return batch

    async def update(self, batch: Batch, *, updates: Mapping[str, object]) -> Batch:
        for field, value in updates.items():
            setattr(batch, field, value)
        await self._session.flush()
        return await self.refresh_response(batch)

    async def complete(self, batch: Batch, *, completed_at: datetime) -> Batch:
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = completed_at
        await self._session.flush()
        return await self.refresh_response(batch)

    async def set_archived(self, batch: Batch, *, archived_at: datetime | None) -> Batch:
        batch.archived_at = archived_at
        await self._session.flush()
        return await self.refresh_response(batch)

    async def search(
        self,
        *,
        q: str | None,
        status: BatchStatus | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
        production_order_id: UUID | None = None,
        without_production_order: bool = False,
    ) -> tuple[list[Batch], int]:
        filters: list[ColumnElement[bool]] = [
            Batch.archived_at.is_not(None) if archived else Batch.archived_at.is_(None)
        ]
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(or_(Batch.name.ilike(pattern), Batch.description.ilike(pattern)))
        if production_order_id is not None:
            filters.append(Batch.production_order_id == production_order_id)
        if without_production_order:
            filters.append(Batch.production_order_id.is_(None))
        if status is not None:
            filters.append(Batch.status == status)
        column = {
            "name": Batch.name,
            "planned_qty": Batch.planned_qty,
            "day_plan_qty": Batch.day_plan_qty,
            "status": Batch.status,
            "created_at": Batch.created_at,
            "updated_at": Batch.updated_at,
            "completed_at": Batch.completed_at,
            "archived_at": Batch.archived_at,
        }[sort]
        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        statement = (
            select(Batch)
            .options(*self._response_options())
            .where(*filters)
            .order_by(sorted_column, Batch.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(select(func.count()).select_from(Batch).where(*filters))
        result = await self._session.execute(statement)
        return list(result.scalars()), int(count or 0)

    async def exists_by_dev_eui_prefix(self, prefix: str) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(Batch.dev_eui_prefix == prefix)))
        )

    async def exists_by_kg_version_id(self, version_id: UUID) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(Batch.kg_version_id == version_id)))
        )
