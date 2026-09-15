from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from loguru import logger

from app.audit.types import AuditActor, AuditEntity
from app.audit.writer import TransactionalAuditWriter
from app.domains.quality.defects.exceptions import DefectGroupArchivedError
from app.domains.quality.defects.repository import DefectGroupRepository

from ..exceptions import PakTestConfigurationError
from ..model import PakTest
from ..repository import PakTestRepository
from ..rules import ensure_observation_group_active


class ObservingPak(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def code(self) -> str: ...

    @property
    def oauth_client_id(self) -> str: ...


class ObservePakTest:
    """Upsert one catalogue definition reported by a PAK in the caller UoW."""

    def __init__(
        self,
        groups: DefectGroupRepository,
        tests: PakTestRepository,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._groups = groups
        self._tests = tests
        self._audit = audit

    async def execute(
        self,
        *,
        pak: ObservingPak,
        test_name: str,
        test_label: str,
        defect_group_code: str,
        seen_at: datetime | None = None,
    ) -> PakTest:
        observed_at = seen_at or datetime.now(UTC)
        group = await self._groups.get_by_code(defect_group_code, for_update=True)
        if group is None:
            self._configuration_error(
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
        try:
            ensure_observation_group_active(group)
        except DefectGroupArchivedError as exc:
            self._configuration_error(
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
            ) from exc
        item = await self._tests.get_by_test_name(test_name)
        if item is None:
            item = await self._tests.create(
                test_name=test_name,
                test_label=test_label,
                defect_group_id=group.id,
                last_seen_at=observed_at,
            )
            await self._audit.record(
                actor=self._actor(pak),
                action="pak_test.created",
                entity=self._entity(item),
                new_data={
                    "test_name": item.test_name,
                    "test_label": item.test_label,
                    "defect_group_id": str(item.defect_group_id),
                    "defect_group_code": group.code,
                },
            )
            return item
        old_data: dict[str, object] = {}
        new_data: dict[str, object] = {}
        if item.test_label != test_label:
            old_data["test_label"] = item.test_label
            new_data["test_label"] = test_label
        if item.defect_group_id != group.id:
            old_data["defect_group_id"] = str(item.defect_group_id)
            new_data["defect_group_id"] = str(group.id)
            old_group = await self._groups.get(item.defect_group_id)
            old_data["defect_group_code"] = old_group.code if old_group is not None else None
            new_data["defect_group_code"] = group.code
        item = await self._tests.update_observation(
            item, test_label=test_label, defect_group_id=group.id, last_seen_at=observed_at
        )
        if new_data:
            await self._audit.record(
                actor=self._actor(pak),
                action="pak_test.updated",
                entity=self._entity(item),
                old_data=old_data,
                new_data=new_data,
            )
        return item

    @staticmethod
    def _actor(pak: ObservingPak) -> AuditActor:
        return AuditActor(
            type="pak", id=str(pak.id), display_name=pak.code, identifier=pak.oauth_client_id
        )

    @staticmethod
    def _entity(item: PakTest) -> AuditEntity:
        return AuditEntity(
            type="pak_test",
            id=str(item.id),
            display_name=item.test_label,
            identifier=item.test_name,
        )

    @staticmethod
    def _configuration_error(
        *, pak: ObservingPak, test_name: str, defect_group_code: str, reason: str
    ) -> None:
        logger.bind(
            event="pak_test.configuration_error",
            pak_id=str(pak.id),
            pak_code=pak.code,
            test_name=test_name,
            defect_group_code=defect_group_code,
            reason=reason,
        ).warning("PAK test references an invalid defect group")
