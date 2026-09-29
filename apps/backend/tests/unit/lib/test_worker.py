from typing import cast

import pytest

from app.config import get_settings
from app.lib.worker import WorkerContext, on_shutdown, on_startup

pytestmark = [pytest.mark.anyio, pytest.mark.unit]


async def test_on_startup_shares_settings_and_database_config() -> None:
    ctx = cast("WorkerContext", {})

    await on_startup(ctx)

    assert ctx["settings"] is get_settings()
    assert str(ctx["alchemy"].connection_string) == str(get_settings().db.database_url)


async def test_on_shutdown_without_startup_does_nothing() -> None:
    ctx = cast("WorkerContext", {})

    await on_shutdown(ctx)

    assert "alchemy" not in ctx


async def test_on_shutdown_disposes_the_engine() -> None:
    ctx = cast("WorkerContext", {})
    await on_startup(ctx)
    engine = ctx["alchemy"].get_engine()
    pool = engine.pool

    await on_shutdown(ctx)

    assert engine.pool is not pool
