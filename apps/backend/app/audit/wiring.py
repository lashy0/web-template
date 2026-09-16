from sqlalchemy.ext.asyncio import AsyncSession

from .repository import AuditRepository


def create_repository(session: AsyncSession) -> AuditRepository:
    return AuditRepository(session)
