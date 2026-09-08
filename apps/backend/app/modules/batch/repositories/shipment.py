from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BatchShipment, BatchShipmentItem


class BatchShipmentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        batch_id: UUID,
        comment: str | None,
        created_by_user_id: UUID | None,
    ) -> BatchShipment:
        shipment = BatchShipment(
            batch_id=batch_id,
            comment=comment,
            created_by_user_id=created_by_user_id,
        )

        self._session.add(shipment)

        await self._session.flush()
        await self._session.refresh(shipment)

        return shipment

    async def get_by_id(self, shipment_id: UUID) -> BatchShipment | None:
        return await self._session.get(BatchShipment, shipment_id)

    async def update_details(
        self,
        shipment: BatchShipment,
        *,
        updates: Mapping[str, object],
    ) -> BatchShipment:
        for field, value in updates.items():
            setattr(shipment, field, value)

        await self._session.flush()
        await self._session.refresh(shipment)

        return shipment

    async def complete(
        self,
        shipment: BatchShipment,
        *,
        completed_at: datetime,
    ) -> BatchShipment:
        shipment.completed_at = completed_at

        await self._session.flush()
        await self._session.refresh(shipment)

        return shipment

    async def void(
        self,
        shipment: BatchShipment,
        *,
        voided_at: datetime,
        reason: str,
    ) -> BatchShipment:
        shipment.voided_at = voided_at
        shipment.void_reason = reason

        await self._session.flush()
        await self._session.refresh(shipment)

        return shipment

    async def add_item(
        self,
        *,
        shipment_id: UUID,
        kg_dev_eui: str,
    ) -> BatchShipmentItem:
        item = BatchShipmentItem(
            shipment_id=shipment_id,
            kg_dev_eui=kg_dev_eui,
        )

        self._session.add(item)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def get_item(
        self,
        *,
        shipment_id: UUID,
        kg_dev_eui: str,
    ) -> BatchShipmentItem | None:
        return await self._session.get(
            BatchShipmentItem,
            (shipment_id, kg_dev_eui),
        )

    async def delete_item(self, item: BatchShipmentItem) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def list_items(self, shipment_id: UUID) -> list[BatchShipmentItem]:
        statement = (
            select(BatchShipmentItem)
            .where(BatchShipmentItem.shipment_id == shipment_id)
            .order_by(
                BatchShipmentItem.created_at.asc(),
                BatchShipmentItem.kg_dev_eui.asc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars())

    async def count_items_by_batch(self, batch_id: UUID) -> dict[UUID, int]:
        result = await self._session.execute(
            select(BatchShipmentItem.shipment_id, func.count())
            .join(
                BatchShipment,
                BatchShipment.id == BatchShipmentItem.shipment_id
            )
            .where(BatchShipment.batch_id == batch_id)
            .group_by(BatchShipmentItem.shipment_id)
        )

        return {shipment_id: int(count) for shipment_id, count in result.tuples()}

    async def count_items(self, shipment_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(BatchShipmentItem)
            .where(BatchShipmentItem.shipment_id == shipment_id)
        )

        return int(count or 0)

    async def find_non_voided_by_kg(self, kg_dev_eui: str) -> BatchShipment | None:
        statement = (
            select(BatchShipment)
            .join(
                BatchShipmentItem,
                BatchShipmentItem.shipment_id == BatchShipment.id,
            )
            .where(
                BatchShipmentItem.kg_dev_eui == kg_dev_eui,
                BatchShipment.voided_at.is_(None),
            )
            .limit(1)
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_batch(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchShipment]:
        filters: list[ColumnElement[bool]] = [
            BatchShipment.batch_id == batch_id,
        ]

        if not include_voided:
            filters.append(BatchShipment.voided_at.is_(None))

        statement = (
            select(BatchShipment)
            .where(*filters)
            .order_by(
                BatchShipment.created_at.desc(),
                BatchShipment.id.asc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars())

    async def get_shipped_total(self, batch_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(BatchShipmentItem)
            .join(
                BatchShipment,
                BatchShipment.id == BatchShipmentItem.shipment_id,
            )
            .where(
                BatchShipment.batch_id == batch_id,
                BatchShipment.completed_at.is_not(None),
                BatchShipment.voided_at.is_(None),
            )
        )

        return int(total or 0)

    async def exists_by_batch(self, batch_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(BatchShipment.batch_id == batch_id))
            )
        )
