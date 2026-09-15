from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.domains.production.batches.model import Batch

# Residual debt: KG embeds a quality-owned subquery in its own SELECTs. A read
# port should replace this SQL-level coupling (see docs/architecture.md).
from app.domains.quality.verification.adapters import latest_verification_projection

from .model import KgDevEuiPrefix, KgState, KgUnit, KgVersion, LoRaWanCredentials
from .projections import current_kg_state_expression
from .schemas.state import KgCurrentState
from .schemas.unit import KgBatchListItem


@dataclass(frozen=True, slots=True)
class KgListItem:
    kg: KgUnit
    current_state: KgCurrentState


class KgRepository:
    """Persistence and PostgreSQL concurrency primitives for the migrated KG slice."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_prefix(self, prefix: str, *, for_update: bool = False) -> KgDevEuiPrefix | None:
        return await self._session.get(
            KgDevEuiPrefix,
            prefix,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_prefix_by_short_code(self, short_code: str) -> KgDevEuiPrefix | None:
        return (
            await self._session.scalars(
                select(KgDevEuiPrefix).where(KgDevEuiPrefix.short_code == short_code).limit(1)
            )
        ).first()

    async def list_prefixes(
        self, *, q: str | None, archived: bool, page: int, page_size: int, sort: str, order: str
    ) -> tuple[list[tuple[KgDevEuiPrefix, int]], int]:
        filters: list[ColumnElement[bool]] = [
            KgDevEuiPrefix.archived_at.is_not(None)
            if archived
            else KgDevEuiPrefix.archived_at.is_(None)
        ]
        if q:
            pattern = f"%{q}%"
            filters.append(
                or_(
                    KgDevEuiPrefix.prefix.ilike(pattern),
                    KgDevEuiPrefix.short_code.ilike(pattern),
                    KgDevEuiPrefix.name.ilike(pattern),
                )
            )
        column = {
            "prefix": KgDevEuiPrefix.prefix,
            "name": KgDevEuiPrefix.name,
            "short_code": KgDevEuiPrefix.short_code,
            "created_at": KgDevEuiPrefix.created_at,
            "archived_at": KgDevEuiPrefix.archived_at,
        }[sort]
        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        counts = (
            select(Batch.dev_eui_prefix.label("prefix"), func.count(Batch.id).label("batch_count"))
            .group_by(Batch.dev_eui_prefix)
            .subquery()
        )
        result = await self._session.execute(
            select(KgDevEuiPrefix, func.coalesce(counts.c.batch_count, 0).label("batch_count"))
            .outerjoin(counts, counts.c.prefix == KgDevEuiPrefix.prefix)
            .where(*filters)
            .order_by(sorted_column, KgDevEuiPrefix.prefix.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(KgDevEuiPrefix).where(*filters)
        )
        return [(item, int(batch_count)) for item, batch_count in result.tuples()], int(count or 0)

    async def count_batches_for_prefix(self, prefix: str) -> int:
        count = await self._session.scalar(
            select(func.count(Batch.id)).where(Batch.dev_eui_prefix == prefix)
        )
        return int(count or 0)

    async def save_prefix(self, item: KgDevEuiPrefix) -> KgDevEuiPrefix:
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def delete_prefix(self, item: KgDevEuiPrefix) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def get_version(self, version_id: UUID, *, for_update: bool = False) -> KgVersion | None:
        return await self._session.get(
            KgVersion, version_id, with_for_update=for_update, populate_existing=for_update
        )

    async def get_version_by_code(self, code: str) -> KgVersion | None:
        return (
            await self._session.scalars(select(KgVersion).where(KgVersion.code == code).limit(1))
        ).first()

    async def list_versions(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[KgVersion, int]], int]:
        filters: list[ColumnElement[bool]] = [
            KgVersion.archived_at.is_not(None) if archived else KgVersion.archived_at.is_(None)
        ]
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    KgVersion.code.ilike(pattern),
                    KgVersion.name.ilike(pattern),
                    KgVersion.description.ilike(pattern),
                )
            )
        column = {
            "code": KgVersion.code,
            "name": KgVersion.name,
            "description": KgVersion.description,
            "created_at": KgVersion.created_at,
            "updated_at": KgVersion.updated_at,
            "archived_at": KgVersion.archived_at,
        }[sort_by]
        sorted_column = (
            column.desc().nulls_last() if sort_order == "desc" else column.asc().nulls_last()
        )
        counts = (
            select(
                Batch.kg_version_id.label("version_id"), func.count(Batch.id).label("batch_count")
            )
            .where(Batch.kg_version_id.is_not(None))
            .group_by(Batch.kg_version_id)
            .subquery()
        )
        result = await self._session.execute(
            select(KgVersion, func.coalesce(counts.c.batch_count, 0).label("batch_count"))
            .outerjoin(counts, counts.c.version_id == KgVersion.id)
            .where(*filters)
            .order_by(sorted_column, KgVersion.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = await self._session.scalar(
            select(func.count()).select_from(KgVersion).where(*filters)
        )
        return [(item, int(batch_count)) for item, batch_count in result.tuples()], int(count or 0)

    async def count_batches_for_version(self, version_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count(Batch.id)).where(Batch.kg_version_id == version_id)
        )
        return int(count or 0)

    async def save_version(self, item: KgVersion) -> KgVersion:
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def delete_version(self, item: KgVersion) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def lock_allocation(self, prefix: str) -> None:
        await self._session.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"kg-dev-eui:{prefix}")))
        )

    async def get_max_dev_eui_for_prefix(self, prefix: str) -> str | None:
        return cast(
            str | None,
            await self._session.scalar(
                select(func.max(KgUnit.dev_eui)).where(KgUnit.dev_eui.like(f"{prefix}%"))
            ),
        )

    async def create_many(
        self, *, dev_euis: Sequence[str], short_code: str, batch_id: UUID
    ) -> list[KgUnit]:
        items = [
            KgUnit(
                dev_eui=dev_eui,
                short_id=f"{short_code}-{dev_eui[-6:]}",
                batch_id=batch_id,
                state=KgState.REGISTERED,
            )
            for dev_eui in dev_euis
        ]
        if not items:
            return []
        self._session.add_all(items)
        await self._session.flush()
        return items

    async def get_by_dev_eui(self, dev_eui: str, *, for_update: bool = False) -> KgUnit | None:
        return await self._session.get(
            KgUnit, dev_eui, with_for_update=for_update, populate_existing=for_update
        )

    async def get_many_by_dev_euis(
        self, dev_euis: Sequence[str], *, for_update: bool = False
    ) -> list[KgUnit]:
        if not dev_euis:
            return []
        statement = select(KgUnit).where(KgUnit.dev_eui.in_(dev_euis)).order_by(KgUnit.dev_eui)
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return list((await self._session.scalars(statement)).all())

    async def list_by_batch(self, batch_id: UUID, *, for_update: bool = False) -> list[KgUnit]:
        statement = select(KgUnit).where(KgUnit.batch_id == batch_id).order_by(KgUnit.dev_eui.asc())
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return list((await self._session.scalars(statement)).all())

    async def get_with_current_state(self, dev_eui: str) -> KgListItem | None:
        latest = latest_verification_projection()
        state = current_kg_state_expression(cast(ColumnElement[object], KgUnit.state), latest)
        row = (
            (
                await self._session.execute(
                    select(KgUnit, state)
                    .outerjoin(
                        latest, and_(latest.c.rank == 1, KgUnit.dev_eui == latest.c.kg_dev_eui)
                    )
                    .where(KgUnit.dev_eui == dev_eui)
                )
            )
            .tuples()
            .one_or_none()
        )
        return None if row is None else KgListItem(row[0], KgCurrentState(row[1]))

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
            filters.append(or_(KgUnit.dev_eui.ilike(pattern), KgUnit.short_id.ilike(pattern)))
        if batch_id is not None:
            filters.append(KgUnit.batch_id == batch_id)
        latest = latest_verification_projection()
        state = current_kg_state_expression(cast(ColumnElement[object], KgUnit.state), latest)
        if current_state is not None:
            filters.append(state == current_state)
        column = {
            "dev_eui": KgUnit.dev_eui,
            "batch_id": KgUnit.batch_id,
            "current_state": state,
            "created_at": KgUnit.created_at,
            "updated_at": KgUnit.updated_at,
        }[sort]
        sorted_column = column.desc() if order == "desc" else column.asc()
        rows = list(
            (
                await self._session.execute(
                    select(KgUnit, state, func.count().over().label("total"))
                    .outerjoin(
                        latest, and_(latest.c.rank == 1, KgUnit.dev_eui == latest.c.kg_dev_eui)
                    )
                    .where(*filters)
                    .order_by(sorted_column, KgUnit.dev_eui.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples()
        )
        return [KgListItem(kg, KgCurrentState(value)) for kg, value, _ in rows], int(
            rows[0][2]
        ) if rows else 0

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
        latest = latest_verification_projection()
        state = current_kg_state_expression(cast(ColumnElement[object], KgUnit.state), latest)
        if current_state is not None:
            filters.append(state == current_state)
        rows = list(
            (
                await self._session.execute(
                    select(
                        KgUnit.dev_eui,
                        state,
                        latest.c.firmware_version,
                        latest.c.started_at,
                        func.count().over().label("total"),
                    )
                    .outerjoin(
                        latest, and_(latest.c.rank == 1, KgUnit.dev_eui == latest.c.kg_dev_eui)
                    )
                    .where(*filters)
                    .order_by(KgUnit.dev_eui.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples()
        )
        return (
            [
                KgBatchListItem(dev_eui, KgCurrentState(value), firmware, started)
                for dev_eui, value, firmware, started, _ in rows
            ],
            int(rows[0][4]) if rows else 0,
        )

    async def has_scrapped_by_batch(self, batch_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(KgUnit.batch_id == batch_id, KgUnit.state == KgState.SCRAPPED)
                )
            )
        )

    async def delete_registered_for_batch(self, batch_id: UUID) -> None:
        # Locking plus state validation belongs here because batch deletion is a SQL workflow.
        units = await self.list_by_batch(batch_id, for_update=True)
        if any(unit.state is not KgState.REGISTERED for unit in units):
            from .exceptions import KgCannotBeDeletedError

            raise KgCannotBeDeletedError
        await self._session.execute(delete(KgUnit).where(KgUnit.batch_id == batch_id))

    async def update_state(self, kg: KgUnit, *, state: KgState) -> KgUnit:
        kg.state = state
        await self._session.flush()
        await self._session.refresh(kg)
        return kg

    async def delete_unit(self, kg: KgUnit) -> None:
        await self._session.delete(kg)
        await self._session.flush()

    async def select_without_credentials_for_batch(
        self, batch_id: UUID, *, limit: int, for_update: bool = False
    ) -> list[KgUnit]:
        statement = (
            select(KgUnit)
            .outerjoin(LoRaWanCredentials, LoRaWanCredentials.kg_dev_eui == KgUnit.dev_eui)
            .where(KgUnit.batch_id == batch_id, LoRaWanCredentials.kg_dev_eui.is_(None))
            .order_by(KgUnit.dev_eui.asc())
            .limit(limit)
        )
        if for_update:
            statement = statement.with_for_update(of=KgUnit)
        return list((await self._session.scalars(statement)).all())

    async def count_credentials_for_batch(self, batch_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(KgUnit)
                .join(LoRaWanCredentials, LoRaWanCredentials.kg_dev_eui == KgUnit.dev_eui)
                .where(KgUnit.batch_id == batch_id)
            )
            or 0
        )

    async def credentials_exist(self, kg_dev_eui: str) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(LoRaWanCredentials.kg_dev_eui == kg_dev_eui))
            )
        )

    async def get_credentials(self, kg_dev_eui: str) -> LoRaWanCredentials | None:
        return await self._session.get(LoRaWanCredentials, kg_dev_eui)

    async def save_credentials(self, item: LoRaWanCredentials) -> LoRaWanCredentials:
        self._session.add(item)
        await self._session.flush()
        return item
