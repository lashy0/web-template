from sqlalchemy.ext.asyncio import AsyncSession

from .queries import CheckQueries
from .repository import CheckRepository


def create_queries(session: AsyncSession) -> CheckQueries:
    return CheckQueries(CheckRepository(session))
