from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..exceptions import DefectGroupAlreadyExistsError, DefectTypeAlreadyExistsError
from ..model import DefectGroup, DefectType
from ..queries import required_group
from ..repository import DefectGroupRepository, DefectTypeRepository
from ..rules import ensure_group_active
from ._common import audit_actor, group_entity, type_entity


class CreateDefectGroup:
    def __init__(self, repository: DefectGroupRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, code: str, name: str, description: str | None
    ) -> DefectGroup:
        if await self._repository.get_by_code(code) is not None:
            raise DefectGroupAlreadyExistsError
        try:
            item = await self._repository.create(code=code, name=name, description=description)
        except IntegrityError as exc:
            raise DefectGroupAlreadyExistsError from exc
        await self._audit.record(
            actor=audit_actor(actor),
            action="defect_group.created",
            entity=group_entity(item),
            new_data={"code": item.code, "name": item.name, "description": item.description},
        )
        return item


class CreateDefectType:
    def __init__(
        self,
        groups: DefectGroupRepository,
        types: DefectTypeRepository,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._groups = groups
        self._types = types
        self._audit = audit

    async def execute(
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
        group = await required_group(self._groups, group_id)
        ensure_group_active(group)
        if await self._types.get_by_code(code) is not None:
            raise DefectTypeAlreadyExistsError
        try:
            item = await self._types.create(
                group_id=group.id,
                code=code,
                name=name,
                description=description,
                possible_cause=possible_cause,
                engineer_action=engineer_action,
            )
        except IntegrityError as exc:
            raise DefectTypeAlreadyExistsError from exc
        await self._audit.record(
            actor=audit_actor(actor),
            action="defect_type.created",
            entity=type_entity(item),
            new_data={
                "group_id": str(item.group_id),
                "code": item.code,
                "name": item.name,
                "description": item.description,
                "possible_cause": item.possible_cause,
                "engineer_action": item.engineer_action,
            },
        )
        return item
