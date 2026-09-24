from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from advanced_alchemy.exceptions import IntegrityError, RepositoryError
from litestar.di import NamedDependency
from loguru import logger
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

type Effect = Callable[[], Awaitable[object]]


class UnitOfWork:
    """Own the commit of one transaction and the effects registered around it."""

    __slots__ = ("_after_commit", "_on_rollback", "session")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._after_commit: list[tuple[str, Effect]] = []
        self._on_rollback: list[tuple[str, Effect]] = []

    def after_commit(self, operation: str, effect: Effect) -> None:
        """Run ``effect`` only after the transaction has been committed."""
        self._after_commit.append((operation, effect))

    def on_rollback(self, operation: str, effect: Effect) -> None:
        """Run ``effect`` as cleanup if the transaction is rolled back."""
        self._on_rollback.append((operation, effect))

    async def commit(self) -> None:
        """Commit, then run post-commit effects.

        Details are fixed so SQL never reaches the client. Constraint violations
        normally surface earlier, at ``flush`` inside a repository, with
        domain-specific messages.

        Raises:
            IntegrityError: A constraint failed at commit (HTTP 409).
            RepositoryError: Any other commit failure, e.g. a lost connection
                or a serialization failure (HTTP 500). The caller must roll back.
        """
        # Advanced Alchemy's ``wrap_sqlalchemy_exception`` is not used here: it
        # maps every ``DBAPIError``, including ``OperationalError``, to
        # ``IntegrityError`` and would answer a lost connection with 409.
        try:
            await self.session.commit()
        except SQLAlchemyIntegrityError as exc:
            raise IntegrityError(detail="The change conflicts with existing data.") from exc
        except SQLAlchemyError as exc:
            raise RepositoryError(detail="The transaction could not be committed.") from exc

        self._on_rollback.clear()
        await _run_effects(self._drain_after_commit(), "Post-commit effect failed")

    async def rollback(self) -> None:
        """Roll back, then run cleanup effects; never raises."""
        self._after_commit.clear()

        try:
            await self.session.rollback()
        except Exception:
            logger.exception("Transaction rollback failed")

        await _run_effects(self._drain_on_rollback(), "Rollback cleanup failed")

    def _drain_after_commit(self) -> list[tuple[str, Effect]]:
        effects, self._after_commit = self._after_commit, []
        return effects

    def _drain_on_rollback(self) -> list[tuple[str, Effect]]:
        effects, self._on_rollback = self._on_rollback, []
        return effects


async def _run_effects(effects: list[tuple[str, Effect]], message: str) -> None:
    for operation, effect in effects:
        try:
            await effect()
        except Exception:
            logger.bind(operation=operation).exception(message)


@asynccontextmanager
async def unit_of_work(session: AsyncSession) -> AsyncGenerator[UnitOfWork]:
    """Commit on success and roll back on error.

    Use directly in CLI commands, background jobs and tests; HTTP handlers get
    the same behaviour from :func:`provide_uow`.
    """
    uow = UnitOfWork(session)

    try:
        yield uow
        await uow.commit()
    except Exception:
        await uow.rollback()
        raise


async def provide_uow(db_session: NamedDependency[AsyncSession]) -> AsyncGenerator[UnitOfWork]:
    """Provide the request unit of work.

    Litestar runs the code after ``yield`` once the handler has returned but
    before the response is sent, and throws handler exceptions into it.
    """
    async with unit_of_work(db_session) as uow:
        yield uow


__all__ = ("Effect", "UnitOfWork", "provide_uow", "unit_of_work")
