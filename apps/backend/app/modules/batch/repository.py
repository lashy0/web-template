from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch.models import (
    Batch,
    BatchReceipt,
    BatchShipment,
    BatchShipmentItem,
    BatchStatus,
)


class BatchRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
        created_by_user_id: UUID | None,
    ) -> Batch:
        batch = Batch(
            name=name,
            description=description,
            dev_eui_prefix=dev_eui_prefix,
            planned_qty=planned_qty,
            day_plan_qty=day_plan_qty,
            status=BatchStatus.IN_PRODUCTION,
            created_by_user_id=created_by_user_id,
        )

        self._session.add(batch)

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def get_by_id(self, batch_id: UUID) -> Batch | None:
        return await self._session.get(Batch, batch_id)

    async def update_details(
        self,
        batch: Batch,
        *,
        updates: Mapping[str, object],
    ) -> Batch:
        for field, value in updates.items():
            setattr(batch, field, value)

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def update_completed(
        self,
        batch: Batch,
        *,
        completed_at: datetime,
    ) -> Batch:
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = completed_at

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def update_archived(
        self,
        batch: Batch,
        *,
        archived_at: datetime | None,
    ) -> Batch:
        batch.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(batch)

        return batch

    async def delete(
        self,
        batch: Batch,
    ) -> None:
        await self._session.delete(batch)
        await self._session.flush()

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
    ) -> tuple[list[Batch], int]:
        filters: list[ColumnElement[bool]] = [
            (
                Batch.archived_at.is_not(None)
                if archived
                else Batch.archived_at.is_(None)
            )
        ]

        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    Batch.name.ilike(pattern),
                    Batch.description.ilike(pattern),
                )
            )

        if status is not None:
            filters.append(Batch.status == status)

        statement = select(Batch).where(*filters)

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

        sorted_column = (
            column.desc().nulls_last()
            if order == "desc"
            else column.asc().nulls_last()
        )

        statement = (
            statement
            .order_by(sorted_column, Batch.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count = await self._session.scalar(
            select(func.count())
            .select_from(Batch)
            .where(*filters)
        )

        result = await self._session.execute(statement)

        return list(result.scalars()), int(count or 0)

    async def exists_by_dev_eui_prefix(self, prefix: str) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        Batch.dev_eui_prefix
                        == prefix
                    )
                )
            )
        )


class BatchReceiptRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        batch_id: UUID,
        quantity: int,
        comment: str | None,
        created_by_user_id: UUID | None,
    ) -> BatchReceipt:
        receipt = BatchReceipt(
            batch_id=batch_id,
            quantity=quantity,
            comment=comment,
            created_by_user_id=created_by_user_id,
        )

        self._session.add(receipt)

        await self._session.flush()
        await self._session.refresh(receipt)

        return receipt

    async def get_by_id(self, receipt_id: UUID) -> BatchReceipt | None:
        return await self._session.get(BatchReceipt, receipt_id)

    async def update_details(
        self,
        receipt: BatchReceipt,
        *,
        updates: Mapping[str, object],
    ) -> BatchReceipt:
        for field, value in updates.items():
            setattr(receipt, field, value)

        await self._session.flush()
        await self._session.refresh(receipt)

        return receipt

    async def void(
        self,
        receipt: BatchReceipt,
        *,
        voided_at: datetime,
        reason: str,
    ) -> BatchReceipt:
        receipt.voided_at = voided_at
        receipt.void_reason = reason

        await self._session.flush()
        await self._session.refresh(receipt)

        return receipt

    async def list_by_batch(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchReceipt]:
        filters: list[ColumnElement[bool]] = [
            BatchReceipt.batch_id == batch_id,
        ]

        if not include_voided:
            filters.append(BatchReceipt.voided_at.is_(None))

        statement = (
            select(BatchReceipt)
            .where(*filters)
            .order_by(
                BatchReceipt.created_at.desc(),
                BatchReceipt.id.asc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars())

    async def get_total(self, batch_id: UUID) -> int:
        total = await self._session.scalar(
            select(
                func.coalesce(
                    func.sum(BatchReceipt.quantity),
                    0,
                )
            )
            .where(
                BatchReceipt.batch_id == batch_id,
                BatchReceipt.voided_at.is_(None),
            )
        )

        return int(total or 0)

    async def exists_by_batch(self, batch_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        BatchReceipt.batch_id == batch_id
                    )
                )
            )
        )


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
        return await self._session.get(
            BatchShipment,
            shipment_id,
        )

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

    async def complete(self,
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

    async def add_item(self, *, shipment_id: UUID, kg_dev_eui: str) -> BatchShipmentItem:
        item = BatchShipmentItem(
            shipment_id=shipment_id,
            kg_dev_eui=kg_dev_eui,
        )

        self._session.add(item)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def get_item(self, *, shipment_id: UUID, kg_dev_eui: str) -> BatchShipmentItem | None:
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
            .where(
                BatchShipmentItem.shipment_id == shipment_id
            )
            .order_by(
                BatchShipmentItem.created_at.asc(),
                BatchShipmentItem.kg_dev_eui.asc(),
            )
        )

        result = await self._session.execute(statement)

        return list(result.scalars())

    async def count_items(self, shipment_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(BatchShipmentItem)
            .where(
                BatchShipmentItem.shipment_id == shipment_id
            )
        )

        return int(count or 0)

    async def find_non_voided_by_kg(self, kg_dev_eui: str) -> BatchShipment | None:
        statement = (
            select(BatchShipment)
            .join(
                BatchShipmentItem,
                BatchShipmentItem.shipment_id
                == BatchShipment.id,
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
            filters.append(
                BatchShipment.voided_at.is_(None)
            )

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
                BatchShipment.id
                == BatchShipmentItem.shipment_id,
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
                select(
                    exists().where(
                        BatchShipment.batch_id == batch_id
                    )
                )
            )
        )
