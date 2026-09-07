from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.kg.exceptions import (
    KgCannotBeDeletedError,
    KgDevEuiPrefixNotFoundError,
    KgDevEuiRangeOverflowError,
    KgInvalidStateError,
    KgNotFoundError,
    KgWrongBatchError,
)

from ..exceptions import (
    BatchCannotBeDeletedError,
    BatchConflictError,
    BatchDevEuiPrefixNotFoundError,
    BatchDevEuiRangeOverflowError,
    BatchShipmentKgNotFoundError,
    BatchShipmentKgNotPackedError,
    BatchShipmentKgWrongBatchError,
)


@asynccontextmanager
async def transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """All entity changes and audit records commit or roll back together."""
    try:
        async with session_factory() as session, session.begin():
            yield session

    except KgCannotBeDeletedError as exc:
        raise BatchCannotBeDeletedError from exc

    except KgDevEuiPrefixNotFoundError as exc:
        raise BatchDevEuiPrefixNotFoundError from exc

    except KgDevEuiRangeOverflowError as exc:
        raise BatchDevEuiRangeOverflowError from exc

    except KgNotFoundError as exc:
        raise BatchShipmentKgNotFoundError from exc

    except KgWrongBatchError as exc:
        raise BatchShipmentKgWrongBatchError from exc

    except KgInvalidStateError as exc:
        raise BatchShipmentKgNotPackedError from exc

    except IntegrityError as exc:
        raise BatchConflictError from exc
