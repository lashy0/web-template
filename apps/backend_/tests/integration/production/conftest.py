"""Production domain integration test fixtures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import pytest

from app.domain.production.schemas import BatchCreate, BatchReceiptCreate
from app.domain.production.services import (
    BatchReceiptService,
    BatchService,
    KgPrefixService,
    KgUnitService,
    KgVersionService,
    PackingService,
    ProductionOrderService,
)
from app.lib.lorawan import ActivationType, LoRaWanVersion
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import models as m


pytestmark = pytest.mark.anyio

type CreateOrder = Callable[..., Awaitable[m.ProductionOrder]]
type CreatePrefix = Callable[..., Awaitable[m.KgPrefix]]
type CreateVersion = Callable[..., Awaitable[m.KgVersion]]
type CreateBatch = Callable[..., Awaitable[m.Batch]]
type CreateReceipt = Callable[..., Awaitable[m.BatchReceipt]]


@pytest.fixture
async def production_order_service(session: AsyncSession) -> AsyncGenerator[ProductionOrderService]:
    """Create ProductionOrderService instance with the test session."""
    async with ProductionOrderService.new(session) as service:
        yield service


@pytest.fixture
async def kg_prefix_service(session: AsyncSession) -> AsyncGenerator[KgPrefixService]:
    """Create KgPrefixService instance with the test session."""
    async with KgPrefixService.new(session) as service:
        yield service


@pytest.fixture
async def kg_version_service(session: AsyncSession) -> AsyncGenerator[KgVersionService]:
    """Create KgVersionService instance with the test session."""
    async with KgVersionService.new(session) as service:
        yield service


@pytest.fixture
async def batch_service(session: AsyncSession) -> AsyncGenerator[BatchService]:
    """Create BatchService instance with the test session."""
    async with BatchService.new(session) as service:
        yield service


@pytest.fixture
async def batch_receipt_service(session: AsyncSession) -> AsyncGenerator[BatchReceiptService]:
    """Create BatchReceiptService instance with the test session."""
    async with BatchReceiptService.new(session) as service:
        yield service


@pytest.fixture
async def kg_unit_service(session: AsyncSession) -> AsyncGenerator[KgUnitService]:
    """Create KgUnitService instance with the test session."""
    async with KgUnitService.new(session) as service:
        yield service


@pytest.fixture
async def packing_service(session: AsyncSession) -> AsyncGenerator[PackingService]:
    """Create PackingService instance with the test session."""
    async with PackingService.new(session) as service:
        yield service


@pytest.fixture
def create_order(
    session: AsyncSession,
    production_order_service: ProductionOrderService,
) -> CreateOrder:
    """Return a helper that commits a production order, archived when requested."""

    async def _create(name: str = "Order", *, archived: bool = False) -> m.ProductionOrder:
        async with unit_of_work(session):
            order = await production_order_service.create({"name": name}, auto_commit=False)

            if archived:
                order = await production_order_service.set_archived(order.id, archived=True)

        return order

    return _create


@pytest.fixture
def create_prefix(session: AsyncSession, kg_prefix_service: KgPrefixService) -> CreatePrefix:
    """Return a helper that commits a DevEUI prefix, archived when requested."""

    async def _create(
        prefix: str = "a1b2c3d4e5",
        short_code: str = "ab1",
        *,
        archived: bool = False,
    ) -> m.KgPrefix:
        async with unit_of_work(session):
            item = await kg_prefix_service.create_prefix({"prefix": prefix, "short_code": short_code})

            if archived:
                item = await kg_prefix_service.set_archived(item.id, archived=True)

        return item

    return _create


@pytest.fixture
def create_version(session: AsyncSession, kg_version_service: KgVersionService) -> CreateVersion:
    """Return a helper that commits a KG version, archived when requested."""

    async def _create(code: str = "v1", *, archived: bool = False) -> m.KgVersion:
        async with unit_of_work(session):
            item = await kg_version_service.create_version({"code": code, "name": f"Version {code}"})

            if archived:
                item = await kg_version_service.set_archived(item.id, archived=True)

        return item

    return _create


@pytest.fixture
def create_batch(
    session: AsyncSession,
    batch_service: BatchService,
    create_prefix: CreatePrefix,
) -> CreateBatch:
    """Return a helper that commits a batch with its KG units, from a new prefix unless one is given."""

    async def _create(
        prefix: m.KgPrefix | None = None,
        *,
        planned_qty: int = 3,
        production_order_id: UUID | None = None,
        archived: bool = False,
    ) -> m.Batch:
        prefix = prefix or await create_prefix()

        async with unit_of_work(session):
            batch = await batch_service.create_batch(
                BatchCreate(
                    name="Batch",
                    kg_prefix_id=prefix.id,
                    planned_qty=planned_qty,
                    day_plan_qty=planned_qty,
                    activation_type=ActivationType.OTAA,
                    lorawan_version=LoRaWanVersion.V1_0,
                    production_order_id=production_order_id,
                ),
                created_by_id=None,
            )

            if archived:
                batch = await batch_service.set_archived(batch.id, archived=True)

        return batch

    return _create


@pytest.fixture
def create_receipt(session: AsyncSession, batch_receipt_service: BatchReceiptService) -> CreateReceipt:
    """Return a helper that commits a receipt of the batch."""

    async def _create(batch: m.Batch, quantity: int = 1) -> m.BatchReceipt:
        async with unit_of_work(session):
            return await batch_receipt_service.create_receipt(
                batch.id,
                BatchReceiptCreate(quantity=quantity),
                created_by_id=None,
            )

    return _create
