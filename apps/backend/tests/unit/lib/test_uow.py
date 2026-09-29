from unittest.mock import AsyncMock

import pytest
from advanced_alchemy.exceptions import IntegrityError, RepositoryError
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.exc import OperationalError

from app.lib.uow import UnitOfWork, unit_of_work

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
]


async def test_unit_of_work_commits_on_success() -> None:
    session = AsyncMock()

    async with unit_of_work(session):
        pass

    session.commit.assert_awaited_once()


async def test_after_commit_effect_runs_after_commit() -> None:
    calls: list[str] = []
    session = AsyncMock()
    session.commit.side_effect = lambda: calls.append("commit")

    async with unit_of_work(session) as uow:
        uow.after_commit("effect", AsyncMock(side_effect=lambda: calls.append("effect")))

    assert calls == ["commit", "effect"]


async def test_failed_effect_does_not_stop_later_effects() -> None:
    later_effect = AsyncMock()

    async with unit_of_work(AsyncMock()) as uow:
        uow.after_commit("failing", AsyncMock(side_effect=RuntimeError("kratos down")))
        uow.after_commit("later", later_effect)

    later_effect.assert_awaited_once()


async def test_unit_of_work_rolls_back_on_error() -> None:
    session = AsyncMock()

    with pytest.raises(ValueError):
        async with unit_of_work(session):
            raise ValueError("handler failed")

    session.rollback.assert_awaited_once()


async def test_rollback_runs_cleanup() -> None:
    cleanup = AsyncMock()

    with pytest.raises(ValueError):
        async with unit_of_work(AsyncMock()) as uow:
            uow.on_rollback("cleanup", cleanup)

            raise ValueError("handler failed")

    cleanup.assert_awaited_once()


async def test_rollback_skips_after_commit_effects() -> None:
    effect = AsyncMock()

    with pytest.raises(ValueError):
        async with unit_of_work(AsyncMock()) as uow:
            uow.after_commit("effect", effect)

            raise ValueError("handler failed")

    effect.assert_not_awaited()


async def test_failed_rollback_still_runs_cleanup() -> None:
    session = AsyncMock()
    session.rollback.side_effect = OSError("connection lost")
    cleanup = AsyncMock()

    with pytest.raises(ValueError):
        async with unit_of_work(session) as uow:
            uow.on_rollback("cleanup", cleanup)

            raise ValueError("handler failed")

    cleanup.assert_awaited_once()


async def test_rollback_after_commit_skips_cleanup() -> None:
    cleanup = AsyncMock()
    uow = UnitOfWork(AsyncMock())
    uow.on_rollback("cleanup", cleanup)
    await uow.commit()

    await uow.rollback()

    cleanup.assert_not_awaited()


async def test_commit_conflict_is_integrity_error() -> None:
    session = AsyncMock()
    session.commit.side_effect = SQLAlchemyIntegrityError("INSERT", {}, Exception("duplicate key"))

    with pytest.raises(IntegrityError):
        async with unit_of_work(session):
            pass


async def test_commit_failure_is_repository_error() -> None:
    session = AsyncMock()
    session.commit.side_effect = OperationalError("COMMIT", {}, Exception("connection lost"))

    with pytest.raises(RepositoryError) as exc_info:
        async with unit_of_work(session):
            pass

    assert not isinstance(exc_info.value, IntegrityError)


async def test_failed_commit_rolls_back() -> None:
    session = AsyncMock()
    session.commit.side_effect = SQLAlchemyIntegrityError("INSERT", {}, Exception("duplicate key"))

    with pytest.raises(IntegrityError):
        async with unit_of_work(session):
            pass

    session.rollback.assert_awaited_once()
