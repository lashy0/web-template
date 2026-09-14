from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contexts.production.production_orders.commands import (
    CreateProductionOrder,
    DeleteProductionOrder,
    SetProductionOrderArchived,
    UpdateProductionOrder,
)
from app.contexts.production.production_orders.exceptions import (
    ProductionOrderCannotBeDeletedError,
)
from app.contexts.production.production_orders.model import ProductionOrder
from app.shared.security import CurrentPrincipal, Role

pytestmark = pytest.mark.unit


def _actor() -> CurrentPrincipal:
    return CurrentPrincipal(uuid4(), uuid4(), uuid4(), Role.MANAGER, "Manager", "manager")


def _order() -> ProductionOrder:
    now = datetime.now(UTC)
    return ProductionOrder(
        id=uuid4(),
        name="September",
        description="First run",
        created_at=now,
        updated_at=now,
    )


class _Repository:
    def __init__(self, item: ProductionOrder, *, has_current_batches: bool = False) -> None:
        self.item = item
        self._has_current_batches = has_current_batches
        self.create = AsyncMock(return_value=item)
        self.update_details = AsyncMock(side_effect=self._update_details)
        self.set_archived = AsyncMock(side_effect=self._set_archived)
        self.delete = AsyncMock()

    async def get(self, order_id, *, for_update=False):  # type: ignore[no-untyped-def]
        return self.item if order_id == self.item.id else None

    async def _update_details(self, item, *, updates):  # type: ignore[no-untyped-def]
        for field, value in updates.items():
            setattr(item, field, value)
        return item

    async def _set_archived(self, item, *, archived_at):  # type: ignore[no-untyped-def]
        item.archived_at = archived_at
        return item

    async def has_current_batches(self, _order_id):  # type: ignore[no-untyped-def]
        return self._has_current_batches


async def test_create_update_and_archive_preserve_audit_snapshots() -> None:
    actor = _actor()
    item = _order()
    repository = _Repository(item)
    audit = SimpleNamespace(record=AsyncMock())

    created = await CreateProductionOrder(repository, audit).execute(
        actor=actor, name=item.name, description=item.description
    )
    updated = await UpdateProductionOrder(repository, audit).execute(
        actor=actor, order_id=item.id, updates={"description": "Updated"}
    )
    archived = await SetProductionOrderArchived(repository, audit).execute(
        actor=actor, order_id=item.id, archived=True
    )
    archived_at = archived.archived_at
    restored = await SetProductionOrderArchived(repository, audit).execute(
        actor=actor, order_id=item.id, archived=False
    )

    assert created is item
    assert updated.description == "Updated"
    assert archived_at is not None
    assert restored.archived_at is None
    assert [call.kwargs["action"] for call in audit.record.await_args_list] == [
        "production_order.created",
        "production_order.updated",
        "production_order.archived",
        "production_order.restored",
    ]
    assert audit.record.await_args_list[1].kwargs["old_data"] == {"description": "First run"}


async def test_delete_uses_current_batch_membership_fact() -> None:
    actor = _actor()
    item = _order()
    audit = SimpleNamespace(record=AsyncMock())
    used_repository = _Repository(item, has_current_batches=True)

    with pytest.raises(ProductionOrderCannotBeDeletedError):
        await DeleteProductionOrder(used_repository, audit).execute(actor=actor, order_id=item.id)
    used_repository.delete.assert_not_awaited()
    audit.record.assert_not_awaited()

    empty_repository = _Repository(item)
    await DeleteProductionOrder(empty_repository, audit).execute(actor=actor, order_id=item.id)
    empty_repository.delete.assert_awaited_once_with(item)
    assert audit.record.await_args.kwargs["action"] == "production_order.deleted"
