"""Quality background tasks run directly against PostgreSQL, as a worker runs them."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import msgspec
import pytest
from advanced_alchemy.extensions.litestar import AsyncSessionConfig, SQLAlchemyAsyncConfig

from app.config import get_settings
from app.db import models as m
from app.db.enums import VerificationSessionStatus
from app.domain.quality.permissions import VerificationPermission
from app.domain.quality.schemas import VerificationSessionOpen
from app.domain.quality.tasks import expire_stale_verification_sessions
from app.lib.realtime import create_realtime
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

    from app.domain.quality.services import VerificationSessionService
    from app.lib.worker import WorkerContext
    from tests.integration.quality.conftest import CreateBatch, CreatePak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


@pytest.fixture
async def ctx(engine: AsyncEngine) -> AsyncGenerator[WorkerContext]:
    """The context a worker gives its tasks, on the test database."""
    realtime = create_realtime(get_settings())
    await realtime.start()

    yield cast(
        "WorkerContext",
        {
            "settings": get_settings(),
            "alchemy": SQLAlchemyAsyncConfig(
                engine_instance=engine,
                session_config=AsyncSessionConfig(expire_on_commit=False),
            ),
            "realtime": realtime,
        },
    )

    await realtime.close()


@pytest.fixture
async def stale_session(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> m.VerificationSession:
    """A running session whose PAK last reported a whole TTL ago."""
    batch = await create_batch()
    pak = await create_pak()

    async with unit_of_work(session):
        item, _ = await verification_service.open_session(
            pak,
            VerificationSessionOpen(
                dev_eui=batch.first_dev_eui,
                slot_no=1,
                firmware_version="1.0.0",
                total_steps=1,
            ),
            reopen_inactivity=timedelta(minutes=60),
        )
        item.last_activity_at = datetime.now(UTC) - get_settings().verification.session_ttl

    return item


async def test_expire_stale_verification_sessions_closes_sessions_idle_past_the_ttl(
    session: AsyncSession,
    ctx: WorkerContext,
    stale_session: m.VerificationSession,
) -> None:
    expired = await expire_stale_verification_sessions(ctx)

    await session.refresh(stale_session)
    assert (expired, stale_session.status) == (1, VerificationSessionStatus.INCOMPLETE)


async def test_expire_stale_verification_sessions_announces_the_change(
    ctx: WorkerContext,
    stale_session: m.VerificationSession,
) -> None:
    async with ctx["realtime"].subscribe({VerificationPermission.READ}) as subscriber:
        await expire_stale_verification_sessions(ctx)
        payload = await subscriber.get()

    assert msgspec.json.decode(payload or b"null") == {
        "type": "verification.changed",
        "data": {"pakId": str(stale_session.pak_id), "batchId": str(stale_session.batch_id)},
    }
