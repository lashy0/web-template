from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.defects.services import DefectGroupService

from ..exceptions import PakTestConfigurationError, PakTestNotFoundError
from ..models import PakDevice, PakTest
from ..repository import PakTestRepository


class PakTestCatalogService:
    """Tracks tests reported by PAK devices."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(self, test_id: UUID) -> PakTest | None:
        async with self._session_factory() as session:
            return await PakTestRepository(session).get_by_id(test_id)

    async def get_by_test_name(self, test_name: str) -> PakTest | None:
        async with self._session_factory() as session:
            return await PakTestRepository(session).get_by_test_name(test_name)

    async def list(
        self,
        *,
        q: str | None,
        defect_group_id: UUID | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[PakTest], int]:
        async with self._session_factory() as session:
            return await PakTestRepository(session).search(
                q=q,
                defect_group_id=defect_group_id,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def observe(
        self,
        *,
        pak: PakDevice,
        test_name: str,
        test_label: str,
        defect_group_code: str,
        seen_at: datetime | None = None,
    ) -> PakTest:
        observed_at = seen_at or datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            return await self.observe_in_session(
                session,
                pak=pak,
                test_name=test_name,
                test_label=test_label,
                defect_group_code=defect_group_code,
                seen_at=observed_at,
            )

    async def observe_in_session(
        self,
        session: AsyncSession,
        *,
        pak: PakDevice,
        test_name: str,
        test_label: str,
        defect_group_code: str,
        seen_at: datetime,
    ) -> PakTest:
        group_repository = DefectGroupService(session)
        test_repository = PakTestRepository(session)

        group = await group_repository.get_group_by_code(defect_group_code, for_update=True)

        if group is None:
            self._log_configuration_error(
                pak=pak,
                test_name=test_name,
                defect_group_code=defect_group_code,
                reason="unknown_defect_group",
            )

            raise PakTestConfigurationError(
                "PAK test references an unknown defect group",
                details={
                    "pak_id": str(pak.id),
                    "pak_code": pak.code,
                    "test_name": test_name,
                    "defect_group_code": defect_group_code,
                },
            )

        if group.archived_at is not None:
            self._log_configuration_error(
                pak=pak,
                test_name=test_name,
                defect_group_code=defect_group_code,
                reason="archived_defect_group",
            )

            raise PakTestConfigurationError(
                "PAK test references an archived defect group",
                details={
                    "pak_id": str(pak.id),
                    "pak_code": pak.code,
                    "test_name": test_name,
                    "defect_group_code": defect_group_code,
                },
            )

        test = await test_repository.get_by_test_name(test_name)

        if test is None:
            test = await test_repository.create(
                test_name=test_name,
                test_label=test_label,
                defect_group_id=group.id,
                last_seen_at=seen_at,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(pak),
                action="pak_test.created",
                entity=self._audit_entity(test),
                new_data={
                    "test_name": test.test_name,
                    "test_label": test.test_label,
                    "defect_group_id": str(test.defect_group_id),
                    "defect_group_code": group.code,
                },
            )

            return test

        old_data: dict[str, object] = {}
        new_data: dict[str, object] = {}

        if test.test_label != test_label:
            old_data["test_label"] = test.test_label
            new_data["test_label"] = test_label

        if test.defect_group_id != group.id:
            old_data["defect_group_id"] = str(test.defect_group_id)
            new_data["defect_group_id"] = str(group.id)

            old_data["defect_group_code"] = await self._get_group_code(
                group_repository,
                test.defect_group_id,
            )
            new_data["defect_group_code"] = group.code

        test = await test_repository.update_observation(
            test,
            test_label=test_label,
            defect_group_id=group.id,
            last_seen_at=seen_at,
        )

        if new_data:
            await AuditService.from_session(session).record(
                actor=self._audit_actor(pak),
                action="pak_test.updated",
                entity=self._audit_entity(test),
                old_data=old_data,
                new_data=new_data,
            )

        return test

    async def require(self, test_id: UUID) -> PakTest:
        test = await self.get(test_id)

        if test is None:
            raise PakTestNotFoundError

        return test

    @staticmethod
    async def _get_group_code(
        repository: DefectGroupService,
        group_id: UUID,
    ) -> str | None:
        group = await repository.get_group(group_id)

        if group is None:
            return None

        return group.code

    @staticmethod
    def _audit_actor(pak: PakDevice) -> AuditActor:
        return AuditActor(
            type="pak",
            id=str(pak.id),
            display_name=pak.code,
            identifier=pak.oauth_client_id,
        )

    @staticmethod
    def _audit_entity(test: PakTest) -> AuditEntity:
        return AuditEntity(
            type="pak_test",
            id=str(test.id),
            display_name=test.test_label,
            identifier=test.test_name,
        )

    @staticmethod
    def _log_configuration_error(
        *,
        pak: PakDevice,
        test_name: str,
        defect_group_code: str,
        reason: str,
    ) -> None:
        logger.bind(
            event="pak_test.configuration_error",
            pak_id=str(pak.id),
            pak_code=pak.code,
            test_name=test_name,
            defect_group_code=defect_group_code,
            reason=reason,
        ).warning("PAK test references an invalid defect group")
