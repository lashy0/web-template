from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService

from ..exceptions import (
    DefectGroupArchivedError,
    DefectTypeAlreadyExistsError,
    DefectTypeCannotBeDeletedError,
)
from ..models import DefectGroup, DefectType
from ..repositories import DefectGroupRepository, DefectTypeRepository
from .audit import _audit_actor, _type_audit_entity
from .queries import _required_group, _required_type


def _ensure_group_not_archived(group: DefectGroup) -> None:
    if group.archived_at is not None:
        raise DefectGroupArchivedError


class DefectTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_type(self, defect_type_id: UUID) -> DefectType | None:
        session = self._session
        return await DefectTypeRepository(session).get_by_id(defect_type_id)

    async def get_type_by_code(self, code: str) -> DefectType | None:
        session = self._session
        return await DefectTypeRepository(session).get_by_code(code)

    async def list_types(
        self,
        *,
        q: str | None,
        group_id: UUID | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[DefectType], int]:
        session = self._session
        return await DefectTypeRepository(session).search(
            q=q,
            group_id=group_id,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

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
        session = self._session
        group_repository = DefectGroupRepository(session)
        type_repository = DefectTypeRepository(session)

        group = await _required_group(group_repository, group_id)

        _ensure_group_not_archived(group)

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
            actor=_audit_actor(actor),
            action="defect_type.created",
            entity=_type_audit_entity(defect_type),
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
        session = self._session
        repository = DefectTypeRepository(session)

        defect_type = await _required_type(repository, defect_type_id)

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
                actor=_audit_actor(actor),
                action="defect_type.updated",
                entity=_type_audit_entity(defect_type),
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
        session = self._session
        group_repository = DefectGroupRepository(session)
        type_repository = DefectTypeRepository(session)

        defect_type = await _required_type(
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

        else:
            if defect_type.archived_at is None:
                return defect_type

            group = await _required_group(
                group_repository,
                defect_type.group_id,
            )

            _ensure_group_not_archived(group)

            defect_type = await type_repository.update_archived(
                defect_type,
                archived_at=None,
            )

            action = "defect_type.restored"

        await AuditService.from_session(session).record(
            actor=_audit_actor(actor),
            action=action,
            entity=_type_audit_entity(defect_type),
        )

        return defect_type

    async def delete_type(
        self,
        *,
        actor: CurrentPrincipal,
        defect_type_id: UUID,
    ) -> None:
        session = self._session
        repository = DefectTypeRepository(session)

        defect_type = await _required_type(
            repository,
            defect_type_id,
        )

        await AuditService.from_session(session).record(
            actor=_audit_actor(actor),
            action="defect_type.deleted",
            entity=_type_audit_entity(defect_type),
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
