from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService

from ..exceptions import (
    ProductionOrderArchivedError,
    ProductionOrderCannotBeDeletedError,
    ProductionOrderNotFoundError,
)
from ..models import ProductionOrder
from ..repository import ProductionOrderRepository
from . import audit, lifecycle


class ProductionOrderService:
    """Writes participate in the caller's explicit transaction, including batch creation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ProductionOrderRepository(session)

    async def get(self, order_id: UUID) -> ProductionOrder | None:
        return await self._repository.get(order_id)

    async def list(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[ProductionOrder, int, int]], int]:
        return await self._repository.search(
            q=q,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def get_totals(self, order_id: UUID) -> tuple[int, int]:
        return await self._repository.get_totals(order_id)

    async def _required(self, order_id: UUID) -> ProductionOrder:
        item = await self._repository.get(order_id, for_update=True)

        if item is None:
            raise ProductionOrderNotFoundError

        return item

    async def assign(self, order_id: UUID) -> ProductionOrder:
        item = await self._required(order_id)

        if item.archived_at is not None:
            raise ProductionOrderArchivedError

        return item

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        name: str,
        description: str | None,
    ) -> ProductionOrder:
        lifecycle.ensure_management_allowed(actor)
        item = await self._repository.create(name=name, description=description)

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            entity=audit.order_entity(item),
            action="production_order.created",
            new_data={
                "name": name,
                "description": description,
            },
        )

        return item

    async def update(
        self,
        order_id: UUID,
        *,
        actor: CurrentPrincipal,
        updates: Mapping[str, object],
    ) -> ProductionOrder:
        lifecycle.ensure_management_allowed(actor)
        item = await self._required(order_id)
        changed = {
            key: value
            for key, value in updates.items()
            if key in ("name", "description") and getattr(item, key) != value
        }

        if changed:
            old = {key: getattr(item, key) for key in changed}
            item = await self._repository.update_details(item, updates=changed)

            await AuditService.from_session(self._session).record(
                actor=audit.actor_identity(actor),
                entity=audit.order_entity(item),
                action="production_order.updated",
                old_data=old,
                new_data=changed,
            )

        return item

    async def set_archived(
        self,
        order_id: UUID,
        *,
        actor: CurrentPrincipal,
        archived: bool,
    ) -> ProductionOrder:
        lifecycle.ensure_management_allowed(actor)
        item = await self._required(order_id)

        if archived != (item.archived_at is not None):
            old = item.archived_at
            item = await self._repository.update_archived(
                item,
                archived_at=datetime.now(UTC) if archived else None,
            )

            await AuditService.from_session(self._session).record(
                actor=audit.actor_identity(actor),
                entity=audit.order_entity(item),
                action="production_order.archived" if archived else "production_order.restored",
                old_data={"archived_at": old.isoformat() if old else None},
                new_data={
                    "archived_at": item.archived_at.isoformat() if item.archived_at else None
                },
            )

        return item

    async def delete(self,
        order_id: UUID,
        *,
        actor: CurrentPrincipal,
    ) -> None:
        lifecycle.ensure_management_allowed(actor)
        item = await self._required(order_id)

        if await self._repository.contains_batches(order_id):
            raise ProductionOrderCannotBeDeletedError

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            entity=audit.order_entity(item),
            action="production_order.deleted",
            old_data={
                "name": item.name,
                "description": item.description,
            },
        )
        await self._repository.delete(item)
