from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService

from ..exceptions import (
    DefectGroupAlreadyExistsError,
    DefectGroupCannotBeDeletedError,
    DefectGroupHasUnarchivedTypesError,
)
from ..models import DefectGroup
from ..repositories import DefectGroupRepository, DefectTypeRepository
from .audit import _audit_actor, _group_audit_entity
from .queries import _required_group


class DefectGroupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_group(self, group_id: UUID) -> DefectGroup | None:
        session = self._session
        return await DefectGroupRepository(session).get_by_id(group_id)

    async def get_group_by_code(
        self,
        code: str,
        *,
        for_update: bool = False,
    ) -> DefectGroup | None:
        session = self._session
        return await DefectGroupRepository(session).get_by_code(code, for_update=for_update)

    async def list_groups(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[DefectGroup, int, int]], int]:
        session = self._session
        return await DefectGroupRepository(session).search(
            q=q,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def create_group(
        self,
        *,
        actor: CurrentPrincipal,
        code: str,
        name: str,
        description: str | None,
    ) -> DefectGroup:
        session = self._session
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
            actor=_audit_actor(actor),
            action="defect_group.created",
            entity=_group_audit_entity(group),
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
        session = self._session
        repository = DefectGroupRepository(session)

        group = await _required_group(repository, group_id)

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
                actor=_audit_actor(actor),
                action="defect_group.updated",
                entity=_group_audit_entity(group),
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
        session = self._session
        group_repository = DefectGroupRepository(session)
        type_repository = DefectTypeRepository(session)

        group = await _required_group(group_repository, group_id)

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
            old_data: dict[str, object] = {
                "archived_at": None,
            }
            new_data: dict[str, object] = {
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
            actor=_audit_actor(actor),
            action=action,
            entity=_group_audit_entity(group),
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
        session = self._session
        group_repository = DefectGroupRepository(session)
        type_repository = DefectTypeRepository(session)

        group = await _required_group(group_repository, group_id)

        if await type_repository.exists_by_group(group.id):
            raise DefectGroupCannotBeDeletedError

        await AuditService.from_session(session).record(
            actor=_audit_actor(actor),
            action="defect_group.deleted",
            entity=_group_audit_entity(group),
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
