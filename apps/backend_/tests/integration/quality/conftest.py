"""Quality domain integration test fixtures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import httpx
import pytest

from app.config import get_settings
from app.db import models as m
from app.db.enums import BatchStatus, PakDeviceKind
from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.services import PakDeviceService
from app.domain.production.schemas import BatchCreate
from app.domain.production.services import BatchService, KgPrefixService
from app.domain.quality.schemas import DefectTypeCreate
from app.domain.quality.services import (
    DefectGroupService,
    DefectTypeService,
    PakCheckService,
    VerificationSessionService,
)
from app.lib.lorawan import ActivationType, LoRaWanVersion
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.lib.hydra import HydraClient
    from tests.conftest import HydraService


pytestmark = pytest.mark.anyio

type CreateGroup = Callable[..., Awaitable[m.DefectGroup]]
type CreateType = Callable[..., Awaitable[m.DefectType]]
type CreateBatch = Callable[..., Awaitable[m.Batch]]
type CreatePak = Callable[..., Awaitable[m.PakDevice]]
type SignInPak = Callable[..., Awaitable[tuple[m.PakDevice, dict[str, str]]]]


@pytest.fixture
async def defect_group_service(session: AsyncSession) -> AsyncGenerator[DefectGroupService]:
    """Create DefectGroupService instance with the test session."""
    async with DefectGroupService.new(session) as service:
        yield service


@pytest.fixture
async def defect_type_service(session: AsyncSession) -> AsyncGenerator[DefectTypeService]:
    """Create DefectTypeService instance with the test session."""
    async with DefectTypeService.new(session) as service:
        yield service


@pytest.fixture
def create_group(session: AsyncSession, defect_group_service: DefectGroupService) -> CreateGroup:
    """Return a helper that commits a defect group, archived when requested."""

    async def _create(code: str = "RF", *, archived: bool = False) -> m.DefectGroup:
        async with unit_of_work(session):
            group = await defect_group_service.create_group({"code": code, "name": f"Group {code}"})

            if archived:
                group = await defect_group_service.set_archived(group.id, archived=True)

        return group

    return _create


@pytest.fixture
def create_type(session: AsyncSession, defect_type_service: DefectTypeService) -> CreateType:
    """Return a helper that commits a defect type of the group, archived when requested."""

    async def _create(
        group: m.DefectGroup,
        code: str = "RF_LOW",
        *,
        archived: bool = False,
    ) -> m.DefectType:
        async with unit_of_work(session):
            defect_type = await defect_type_service.create_type(
                DefectTypeCreate(
                    group_id=group.id,
                    code=code,
                    name=f"Type {code}",
                    description="Weak signal",
                ),
            )

            if archived:
                defect_type = await defect_type_service.set_archived(defect_type.id, archived=True)

        return defect_type

    return _create


@pytest.fixture
async def pak_check_service(session: AsyncSession) -> AsyncGenerator[PakCheckService]:
    """Create PakCheckService instance with the test session."""
    async with PakCheckService.new(session) as service:
        yield service


@pytest.fixture
async def verification_service(session: AsyncSession) -> AsyncGenerator[VerificationSessionService]:
    """Create VerificationSessionService instance with the test session."""
    async with VerificationSessionService.new(session) as service:
        yield service


@pytest.fixture
def create_batch(session: AsyncSession) -> CreateBatch:
    """Return a helper that commits a batch of two KG units under a new DevEUI prefix."""

    async def _create(
        prefix: str = "a1b2c3d4e5",
        *,
        status: BatchStatus = BatchStatus.IN_PRODUCTION,
        archived: bool = False,
    ) -> m.Batch:
        async with (
            unit_of_work(session),
            KgPrefixService.new(session) as prefixes,
            BatchService.new(session) as batches,
        ):
            kg_prefix = await prefixes.create_prefix({"prefix": prefix, "short_code": prefix[-3:]})
            batch = await batches.create_batch(
                BatchCreate(
                    name="Batch",
                    kg_prefix_id=kg_prefix.id,
                    planned_qty=2,
                    day_plan_qty=2,
                    activation_type=ActivationType.OTAA,
                    lorawan_version=LoRaWanVersion.V1_0,
                ),
                created_by_id=None,
            )

            if status is BatchStatus.COMPLETED:
                batch = await batches.complete_batch(batch.id)

            if archived:
                batch = await batches.set_archived(batch.id, archived=True)

        return batch

    return _create


@pytest.fixture
def create_pak(session: AsyncSession) -> CreatePak:
    """Return a helper that commits a PAK row without a Hydra client; services here never call Hydra."""

    async def _create(kind: PakDeviceKind = PakDeviceKind.OTK_LINE) -> m.PakDevice:
        suffix = uuid4().hex[:8]
        pak = m.PakDevice(
            code=f"pak-{suffix}",
            kind=kind,
            oauth_client_id=f"pak-client-{suffix}",
            encrypted_access_key="unused",
        )

        async with unit_of_work(session):
            session.add(pak)

        return pak

    return _create


@pytest.fixture
def sign_in_pak(
    session: AsyncSession,
    hydra_client: HydraClient,
    hydra_service: HydraService,
) -> SignInPak:
    """Return a helper that registers a PAK with a Hydra client and returns it with its bearer headers."""

    async def _sign_in(
        kind: PakDeviceKind = PakDeviceKind.OTK_LINE,
    ) -> tuple[m.PakDevice, dict[str, str]]:
        cipher = PakAccessKeyCipher(get_settings().hydra.pak_access_key_encryption_key)

        async with unit_of_work(session) as uow, PakDeviceService.new(session) as paks:
            pak, access_key = await paks.create_pak(
                {"code": f"pak-{uuid4().hex[:8]}", "kind": kind, "is_active": True},
                hydra=hydra_client,
                cipher=cipher,
                uow=uow,
            )

        async with httpx.AsyncClient(base_url=hydra_service.public_url) as client:
            response = await client.post(
                "/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(pak.oauth_client_id, access_key),
            )
        response.raise_for_status()
        token = cast("str", response.json()["access_token"])

        return pak, {"Authorization": f"Bearer {token}"}

    return _sign_in
