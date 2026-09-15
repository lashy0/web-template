"""Compatibility adapter for verification until its quality slice is migrated."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.contexts.quality.defects.repository import DefectGroupRepository
from app.contexts.quality.tests.commands import ObservePakTest
from app.contexts.quality.tests.model import PakTest
from app.contexts.quality.tests.queries import PakTestQueries
from app.contexts.quality.tests.repository import PakTestRepository

from ..models import PakDevice


class PakTestCatalogService:
    """Legacy import adapter; quality.tests owns catalogue behaviour."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, test_id: UUID) -> PakTest | None:
        async with self._session_factory() as session:
            return await PakTestQueries(PakTestRepository(session)).get(test_id)

    async def get_by_test_name(self, test_name: str) -> PakTest | None:
        async with self._session_factory() as session:
            return await PakTestQueries(PakTestRepository(session)).get_by_test_name(test_name)

    async def list(self, **kwargs: object) -> tuple[list[PakTest], int]:
        async with self._session_factory() as session:
            return await PakTestQueries(PakTestRepository(session)).list(**kwargs)

    async def observe(
        self,
        *,
        pak: PakDevice,
        test_name: str,
        test_label: str,
        defect_group_code: str,
        seen_at: datetime | None = None,
    ) -> PakTest:
        async with self._session_factory() as session, session.begin():
            return await self.observe_in_session(
                session,
                pak=pak,
                test_name=test_name,
                test_label=test_label,
                defect_group_code=defect_group_code,
                seen_at=seen_at,
            )

    async def observe_in_session(
        self,
        session: AsyncSession,
        *,
        pak: PakDevice,
        test_name: str,
        test_label: str,
        defect_group_code: str,
        seen_at: datetime | None = None,
    ) -> PakTest:
        return await ObservePakTest(
            DefectGroupRepository(session),
            PakTestRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(
            pak=pak,
            test_name=test_name,
            test_label=test_label,
            defect_group_code=defect_group_code,
            seen_at=seen_at,
        )

    async def require(self, test_id: UUID) -> PakTest:
        async with self._session_factory() as session:
            return await PakTestQueries(PakTestRepository(session)).require(test_id)
