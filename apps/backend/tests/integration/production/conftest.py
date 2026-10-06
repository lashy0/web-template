"""Production domain integration test fixtures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import func, update

from app.db import models as m
from app.db.enums import KgOtkStatus, KgState, PakDeviceKind
from app.domain.production.schemas import BatchCreate, BatchReceiptCreate, BatchShipmentCreate
from app.domain.production.services import (
    BatchReceiptService,
    BatchService,
    BatchShipmentItemService,
    BatchShipmentService,
    KgPrefixService,
    KgUnitService,
    KgVersionService,
    MulticastGroupService,
    PackingService,
    ProductionOrderService,
)
from app.domain.quality.schemas import (
    VerificationSessionComplete,
    VerificationSessionOpen,
    VerificationSessionResult,
    VerificationStepComplete,
    VerificationStepResult,
    VerificationStepStart,
)
from app.domain.quality.services import PakCheckService, VerificationSessionService
from app.lib.lorawan import ActivationType, LoRaWanVersion
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import MulticastGroups


pytestmark = pytest.mark.anyio

type CreateOrder = Callable[..., Awaitable[m.ProductionOrder]]
type CreatePrefix = Callable[..., Awaitable[m.KgPrefix]]
type CreateVersion = Callable[..., Awaitable[m.KgVersion]]
type CreateBatch = Callable[..., Awaitable[m.Batch]]
type CreateReceipt = Callable[..., Awaitable[m.BatchReceipt]]
type PackUnits = Callable[..., Awaitable[None]]
type CreateShipment = Callable[..., Awaitable[m.BatchShipment]]
type VerifyUnit = Callable[..., Awaitable[m.VerificationSession]]


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
async def multicast_group_service(session: AsyncSession) -> AsyncGenerator[MulticastGroupService]:
    """Create MulticastGroupService instance with the test session."""
    async with MulticastGroupService.new(session) as service:
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
            order = await production_order_service.create_order({"name": name})

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
    multicast_groups: MulticastGroups,
) -> CreateBatch:
    """Return a helper that commits a batch with its KG units, from a new prefix unless one is given."""

    async def _create(
        prefix: m.KgPrefix | None = None,
        *,
        planned_qty: int = 3,
        production_order_id: UUID | None = None,
        kg_version_id: UUID | None = None,
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
                    multicast_group_0_id=multicast_groups[0].id,
                    multicast_group_1_id=multicast_groups[1].id,
                    production_order_id=production_order_id,
                    kg_version_id=kg_version_id,
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


@pytest.fixture
async def batch_shipment_service(session: AsyncSession) -> AsyncGenerator[BatchShipmentService]:
    """Create BatchShipmentService instance with the test session."""
    async with BatchShipmentService.new(session) as service:
        yield service


@pytest.fixture
async def batch_shipment_item_service(session: AsyncSession) -> AsyncGenerator[BatchShipmentItemService]:
    """Create BatchShipmentItemService instance with the test session."""
    async with BatchShipmentItemService.new(session) as service:
        yield service


@pytest.fixture
def pack_units(session: AsyncSession) -> PackUnits:
    """Return a helper that commits the given units as passed OTK and packed, as packing leaves them."""

    async def _pack(*dev_euis: str) -> None:
        async with unit_of_work(session):
            await session.execute(
                update(m.KgUnit)
                .where(m.KgUnit.dev_eui.in_(dev_euis))
                .values(state=KgState.PACKED, otk_status=KgOtkStatus.PASSED, packed_at=func.now())
            )

    return _pack


@pytest.fixture
def create_shipment(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    batch_shipment_item_service: BatchShipmentItemService,
) -> CreateShipment:
    """Return a helper that commits a shipment of the batch with the given packed units, completed when requested."""

    async def _create(batch: m.Batch, *dev_euis: str, completed: bool = False) -> m.BatchShipment:
        async with unit_of_work(session):
            shipment = await batch_shipment_service.create_shipment(
                batch.id,
                BatchShipmentCreate(),
                created_by_id=None,
            )

            if dev_euis:
                shipment, _, _ = await batch_shipment_item_service.add_units(
                    batch.id,
                    shipment.id,
                    dev_euis,
                    added_by_id=None,
                )

            if completed:
                shipment = await batch_shipment_service.complete_shipment(batch.id, shipment.id, completed_by_id=None)

        return shipment

    return _create


@pytest.fixture
def verify_unit(session: AsyncSession) -> VerifyUnit:
    """Return a helper that verifies a unit on a new PAK through the verification service.

    ``steps`` maps each check label to whether it passes; the session passes
    when all do. ``finish=False`` leaves it running after its steps.
    """

    async def _verify(
        dev_eui: str,
        steps: dict[str, bool],
        *,
        kind: PakDeviceKind = PakDeviceKind.OTK_LINE,
        finish: bool = True,
    ) -> m.VerificationSession:
        suffix = uuid4().hex[:8]
        pak = m.PakDevice(
            code=f"pak-{suffix}",
            kind=kind,
            oauth_client_id=f"pak-client-{suffix}",
            encrypted_access_key="unused",
        )

        async with (
            unit_of_work(session),
            VerificationSessionService.new(session=session) as sessions,
            PakCheckService.new(session=session) as checks,
        ):
            session.add(pak)
            await session.flush()
            item, _ = await sessions.open_session(
                pak,
                VerificationSessionOpen(dev_eui=dev_eui, slot_no=1, firmware_version="1.0.0", total_steps=len(steps)),
                reopen_inactivity=timedelta(minutes=60),
            )

            for step_no, (label, passes) in enumerate(steps.items(), start=1):
                await sessions.start_step(
                    pak,
                    item.id,
                    VerificationStepStart(
                        step_no=step_no,
                        check_name=f"check_{step_no}",
                        check_label=label,
                        defect_group_code="RF",
                    ),
                    checks=checks,
                )
                await sessions.complete_step(
                    pak,
                    item.id,
                    step_no,
                    VerificationStepComplete(
                        status=VerificationStepResult.PASSED if passes else VerificationStepResult.FAILED
                    ),
                )

            if finish:
                outcome = VerificationSessionResult.PASSED if all(steps.values()) else VerificationSessionResult.FAILED
                item = await sessions.complete_session(pak, item.id, VerificationSessionComplete(status=outcome))

        return item

    return _verify
