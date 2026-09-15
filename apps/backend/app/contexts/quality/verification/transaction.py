"""Verification's compatibility error boundary around the shared UoW."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.uow import transaction

from .exceptions import VerificationConflictError


@asynccontextmanager
async def verification_transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Retain the legacy translation of a persistence race to API conflict."""
    try:
        async with transaction(session_factory) as session:
            yield session
    except IntegrityError as exc:
        raise VerificationConflictError from exc
