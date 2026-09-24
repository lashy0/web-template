from unittest.mock import AsyncMock

import pytest
from advanced_alchemy.exceptions import IntegrityError
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError

from app.lib.uow import unit_of_work

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
]


async def test_unit_of_work_commits_and_runs_after_commit_effects() -> None:
    session = AsyncMock()
    effect = AsyncMock()

    async with unit_of_work(session) as uow:
        uow.after_commit("effect", effect)

    session.commit.assert_awaited_once()
    effect.assert_awaited_once()


async def test_unit_of_work_rolls_back_on_error() -> None:
    session = AsyncMock()
    effect = AsyncMock()
    cleanup = AsyncMock()

    with pytest.raises(ValueError):
        async with unit_of_work(session) as uow:
            uow.after_commit("effect", effect)
            uow.on_rollback("cleanup", cleanup)

            raise ValueError("handler failed")

    session.rollback.assert_awaited_once()
    cleanup.assert_awaited_once()
    effect.assert_not_awaited()


async def test_unit_of_work_failed_effect_does_not_fail_commit() -> None:
    session = AsyncMock()

    async with unit_of_work(session) as uow:
        uow.after_commit("effect", AsyncMock(side_effect=RuntimeError("kratos down")))

    session.commit.assert_awaited_once()


async def test_unit_of_work_commit_conflict() -> None:
    session = AsyncMock()
    session.commit.side_effect = SQLAlchemyIntegrityError("INSERT", {}, Exception("duplicate key"))

    with pytest.raises(IntegrityError):
        async with unit_of_work(session):
            pass

    session.rollback.assert_awaited_once()
