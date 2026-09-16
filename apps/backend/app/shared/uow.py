"""Transaction boundary with centrally managed post-commit effects.

Commands may register semantic effects with ``uow.after_commit(effect)`` while
changing the database. Production composition currently supplies an in-process
executor; a future outbox executor can consume the same effects unchanged.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol, overload

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class PostCommitExecutor(Protocol):
    """Port responsible for delivering committed semantic effects."""

    async def execute(self, effect: object) -> None: ...


@dataclass(slots=True)
class UnitOfWork:
    """Caller-owned transaction state and its deferred external effects."""

    session: AsyncSession
    executor: PostCommitExecutor | None = None
    _effects: list[object] = field(default_factory=list, init=False)

    def __getattr__(self, name: str) -> object:
        """Temporary compatibility bridge for session-oriented repositories."""
        return getattr(self.session, name)

    def after_commit(self, effect: object) -> None:
        """Best-effort registration that never changes the DB transaction outcome."""
        if effect is None:
            logger.bind(event="post_commit.effect_registration_failed").error(
                "Ignoring an empty post-commit effect"
            )
            return
        try:
            self._effects.append(effect)
        except Exception:
            logger.bind(event="post_commit.effect_registration_failed").exception(
                "Could not register post-commit effect"
            )

    async def run_after_commit(self) -> None:
        """Deliver every registered effect after the database has committed."""
        if self.executor is None:
            if self._effects:
                logger.bind(event="post_commit.executor_missing", count=len(self._effects)).error(
                    "Committed post-commit effects have no executor"
                )
            return
        for effect in self._effects:
            try:
                await self.executor.execute(effect)
            except Exception:
                logger.bind(event="post_commit.effect_execution_failed").exception(
                    "Committed post-commit effect failed"
                )


@overload
def transaction(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    executor: PostCommitExecutor | None,
) -> AbstractAsyncContextManager[UnitOfWork]: ...


@overload
def transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> AbstractAsyncContextManager[AsyncSession]: ...


@asynccontextmanager
async def transaction(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    executor: PostCommitExecutor | None = None,
) -> AsyncIterator[Any]:
    """Commit database work, then best-effort execute its registered effects."""
    async with session_factory() as session:
        uow = UnitOfWork(session, executor)
        async with session.begin():
            yield uow
        await uow.run_after_commit()
