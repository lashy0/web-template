from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.defects.exceptions import (
    DefectGroupAlreadyExistsError,
    DefectGroupArchivedError,
    DefectGroupCannotBeDeletedError,
    DefectGroupHasUnarchivedTypesError,
    DefectGroupNotFoundError,
    DefectTypeAlreadyExistsError,
    DefectTypeCannotBeDeletedError,
    DefectTypeNotFoundError,
)
from app.modules.defects.models import DefectGroup, DefectType
from app.modules.defects.repository import DefectGroupRepository, DefectTypeRepository


class DefectManagementService:
    """Coordinates defect groups, defect types, archive state, and audit."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    # Defect groups

    async def get_group(self, group_id: UUID) -> DefectGroup | None:
        async with self._session_factory() as session:
            return await DefectGroupRepository(session).get_by_id(group_id)

    async def get_group_by_code(self, code: str) -> DefectGroup | None:
        async with self._session_factory() as session:
            return await DefectGroupRepository(session).get_by_code(code)

    async def list_groups(
        self,
        **filters: object,
    ) -> tuple[list[tuple[DefectGroup, int, int]], int]:
        async with self._session_factory() as session:
            return await DefectGroupRepository(session).search(**filters)  # type: ignore[arg-type]

    async def create_group(
        self,
        *,
        actor: CurrentPrincipal,
        code: str,
        name: str,
        description: str | None,
    ) -> DefectGroup:
        async with self._session_factory() as session, session.begin():
            repository = DefectGroupRepository(session)

            if await repository.get_by_code(code) is not None:
                raise DefectGroupAlreadyExistsError

            try:
                group = await repository.create(
                    code=code,
                    name=name,
                    description=description,
                )

            except IntegrityError as exc:
                raise DefectGroupAlreadyExistsError from exc

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="defect_group.created",
                entity=self._group_audit_entity(group),
                new_data={
                    "code": group.code,
                    "name": group.name,
                    "description": group.description,
                },
            )

            return group

    async def update_group(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
        updates: Mapping[str, object],
    ) -> DefectGroup:
        async with self._session_factory() as session, session.begin():
            repository = DefectGroupRepository(session)

            group = await self._required_group(repository, group_id)

            if not updates:
                return group

            old_values = {field: getattr(group, field) for field in updates}

            group = await repository.update_details(
                group,
                updates=updates,
            )

            new_values = {field: getattr(group, field) for field in updates}

            changed = {
                field: value for field, value in new_values.items() if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=self._audit_actor(actor),
                    action="defect_group.updated",
                    entity=self._group_audit_entity(group),
                    old_data={field: old_values[field] for field in changed},
                    new_data=changed,
                )

            return group

    async def set_group_archived(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
        archived: bool,
    ) -> DefectGroup:
        async with self._session_factory() as session, session.begin():
            group_repository = DefectGroupRepository(session)
            type_repository = DefectTypeRepository(session)

            group = await self._required_group(group_repository, group_id)

            if archived:
                if group.archived_at is not None:
                    return group

                if await type_repository.exists_unarchived_by_group(group.id):
                    raise DefectGroupHasUnarchivedTypesError

                archived_at = datetime.now(UTC)

                group = await group_repository.update_archived(
                    group,
                    archived_at=archived_at,
                )

                action = "defect_group.archived"
                old_data = {
                    "archived_at": None,
                }
                new_data = {
                    "archived_at": archived_at.isoformat(),
                }

            else:
                if group.archived_at is None:
                    return group

                old_archived_at = group.archived_at

                group = await group_repository.update_archived(
                    group,
                    archived_at=None,
                )

                action = "defect_group.restored"
                old_data = {
                    "archived_at": old_archived_at.isoformat(),
                }
                new_data = {
                    "archived_at": None,
                }

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action=action,
                entity=self._group_audit_entity(group),
                old_data=old_data,
                new_data=new_data,
            )

            return group

    async def delete_group(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            group_repository = DefectGroupRepository(session)
            type_repository = DefectTypeRepository(session)

            group = await self._required_group(group_repository, group_id)

            if await type_repository.exists_by_group(group.id):
                raise DefectGroupCannotBeDeletedError

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="defect_group.deleted",
                entity=self._group_audit_entity(group),
                old_data={
                    "code": group.code,
                    "name": group.name,
                    "description": group.description,
                    "archived_at": (
                        group.archived_at.isoformat() if group.archived_at is not None else None
                    ),
                },
            )

            try:
                await group_repository.delete(group)

            except IntegrityError as exc:
                raise DefectGroupCannotBeDeletedError from exc

    # Defect types

    async def get_type(self, defect_type_id: UUID) -> DefectType | None:
        async with self._session_factory() as session:
            return await DefectTypeRepository(session).get_by_id(defect_type_id)

    async def get_type_by_code(self, code: str) -> DefectType | None:
        async with self._session_factory() as session:
            return await DefectTypeRepository(session).get_by_code(code)

    async def list_types(self, **filters: object) -> tuple[list[DefectType], int]:
        async with self._session_factory() as session:
            return await DefectTypeRepository(session).search(**filters)  # type: ignore[arg-type]

    async def create_type(
        self,
        *,
        actor: CurrentPrincipal,
        group_id: UUID,
        code: str,
        name: str,
        description: str,
        possible_cause: str | None,
        engineer_action: str | None,
    ) -> DefectType:
        async with self._session_factory() as session, session.begin():
            group_repository = DefectGroupRepository(session)
            type_repository = DefectTypeRepository(session)

            group = await self._required_group(group_repository, group_id)

            self._ensure_group_not_archived(group)

            if await type_repository.get_by_code(code) is not None:
                raise DefectTypeAlreadyExistsError

            try:
                defect_type = await type_repository.create(
                    group_id=group.id,
                    code=code,
                    name=name,
                    description=description,
                    possible_cause=possible_cause,
                    engineer_action=engineer_action,
                )

            except IntegrityError as exc:
                raise DefectTypeAlreadyExistsError from exc

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="defect_type.created",
                entity=self._type_audit_entity(defect_type),
                new_data={
                    "group_id": str(defect_type.group_id),
                    "code": defect_type.code,
                    "name": defect_type.name,
                    "description": defect_type.description,
                    "possible_cause": defect_type.possible_cause,
                    "engineer_action": defect_type.engineer_action,
                },
            )

            return defect_type

    async def update_type(
        self,
        *,
        actor: CurrentPrincipal,
        defect_type_id: UUID,
        updates: Mapping[str, object],
    ) -> DefectType:
        async with self._session_factory() as session, session.begin():
            repository = DefectTypeRepository(session)

            defect_type = await self._required_type(repository, defect_type_id)

            if not updates:
                return defect_type

            old_values = {field: getattr(defect_type, field) for field in updates}

            defect_type = await repository.update_details(
                defect_type,
                updates=updates,
            )

            new_values = {field: getattr(defect_type, field) for field in updates}

            changed = {
                field: value for field, value in new_values.items() if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=self._audit_actor(actor),
                    action="defect_type.updated",
                    entity=self._type_audit_entity(defect_type),
                    old_data={field: old_values[field] for field in changed},
                    new_data=changed,
                )

            return defect_type

    async def set_type_archived(
        self,
        *,
        actor: CurrentPrincipal,
        defect_type_id: UUID,
        archived: bool,
    ) -> DefectType:
        async with self._session_factory() as session, session.begin():
            group_repository = DefectGroupRepository(session)
            type_repository = DefectTypeRepository(session)

            defect_type = await self._required_type(
                type_repository,
                defect_type_id,
            )

            if archived:
                if defect_type.archived_at is not None:
                    return defect_type

                archived_at = datetime.now(UTC)

                defect_type = await type_repository.update_archived(
                    defect_type,
                    archived_at=archived_at,
                )

                action = "defect_type.archived"
                old_data = {
                    "archived_at": None,
                }
                new_data = {
                    "archived_at": archived_at.isoformat(),
                }

            else:
                if defect_type.archived_at is None:
                    return defect_type

                group = await self._required_group(
                    group_repository,
                    defect_type.group_id,
                )

                self._ensure_group_not_archived(group)

                old_archived_at = defect_type.archived_at

                defect_type = await type_repository.update_archived(
                    defect_type,
                    archived_at=None,
                )

                action = "defect_type.restored"
                old_data = {
                    "archived_at": old_archived_at.isoformat(),
                }
                new_data = {
                    "archived_at": None,
                }

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action=action,
                entity=self._type_audit_entity(defect_type),
                old_data=old_data,
                new_data=new_data,
            )

            return defect_type

    async def delete_type(
        self,
        *,
        actor: CurrentPrincipal,
        defect_type_id: UUID,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            repository = DefectTypeRepository(session)

            defect_type = await self._required_type(
                repository,
                defect_type_id,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="defect_type.deleted",
                entity=self._type_audit_entity(defect_type),
                old_data={
                    "group_id": str(defect_type.group_id),
                    "code": defect_type.code,
                    "name": defect_type.name,
                    "description": defect_type.description,
                    "possible_cause": defect_type.possible_cause,
                    "engineer_action": defect_type.engineer_action,
                    "archived_at": (
                        defect_type.archived_at.isoformat()
                        if defect_type.archived_at is not None
                        else None
                    ),
                },
            )

            try:
                await repository.delete(defect_type)

            except IntegrityError as exc:
                raise DefectTypeCannotBeDeletedError from exc

    # Helpers

    @staticmethod
    async def _required_group(
        repository: DefectGroupRepository,
        group_id: UUID,
    ) -> DefectGroup:
        group = await repository.get_by_id(group_id)

        if group is None:
            raise DefectGroupNotFoundError

        return group

    @staticmethod
    async def _required_type(
        repository: DefectTypeRepository,
        defect_type_id: UUID,
    ) -> DefectType:
        defect_type = await repository.get_by_id(defect_type_id)

        if defect_type is None:
            raise DefectTypeNotFoundError

        return defect_type

    @staticmethod
    def _ensure_group_not_archived(group: DefectGroup) -> None:
        if group.archived_at is not None:
            raise DefectGroupArchivedError

    @staticmethod
    def _audit_actor(actor: CurrentPrincipal) -> AuditActor:
        return AuditActor.user(
            actor.user_id,
            name=actor.name,
            login=actor.login,
        )

    @staticmethod
    def _group_audit_entity(group: DefectGroup) -> AuditEntity:
        return AuditEntity(
            type="defect_group",
            id=str(group.id),
            display_name=group.name,
            identifier=group.code,
        )

    @staticmethod
    def _type_audit_entity(defect_type: DefectType) -> AuditEntity:
        return AuditEntity(
            type="defect_type",
            id=str(defect_type.id),
            display_name=defect_type.name,
            identifier=defect_type.code,
        )
