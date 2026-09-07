from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.kg.exceptions import KgInvalidStateError, KgNotFoundError

from ..exceptions import (
    VerificationConflictError,
    VerificationKgNotFoundError,
    VerificationKgNotReadyError,
)


@asynccontextmanager
async def transaction(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    try:
        async with factory() as session, session.begin():
            yield session

    except KgNotFoundError as exc:
        raise VerificationKgNotFoundError from exc

    except KgInvalidStateError as exc:
        raise VerificationKgNotReadyError from exc

    except IntegrityError as exc:
        raise VerificationConflictError from exc
