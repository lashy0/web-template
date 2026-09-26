"""Quality background tasks run directly against PostgreSQL, as a worker runs them."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from advanced_alchemy.extensions.litestar import AsyncSessionConfig, SQLAlchemyAsyncConfig
from sqlalchemy import select

from app.config import get_settings
from app.db import models as m
from app.db.enums import VerificationSessionStatus
from app.domain.quality.schemas import VerificationSessionOpen
from app.domain.quality.tasks import expire_stale_verification_sessions
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

    from app.domain.quality.services import VerificationSessionService
    from app.lib.worker import WorkerContext
    from tests.integration.quality.conftest import CreateBatch, CreatePak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_expire_stale_verification_sessions_closes_sessions_idle_past_the_ttl(
    engine: AsyncEngine,
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()

    async with unit_of_work(session):
        item = await verification_service.open_session(
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
    item_id = item.id
    ctx = cast(
        "WorkerContext",
        {
            "settings": get_settings(),
            "alchemy": SQLAlchemyAsyncConfig(
                engine_instance=engine,
                session_config=AsyncSessionConfig(expire_on_commit=False),
            ),
        },
    )

    expired = await expire_stale_verification_sessions(ctx)

    session.expire_all()
    status = await session.scalar(
        select(m.VerificationSession.status)
        .where(m.VerificationSession.id == item_id)
    )
    assert (expired, status) == (1, VerificationSessionStatus.INCOMPLETE)
