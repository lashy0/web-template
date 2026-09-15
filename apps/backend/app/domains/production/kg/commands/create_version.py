from sqlalchemy.exc import IntegrityError

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..exceptions import KgVersionConflictError
from ..model import KgVersion
from ..permissions import KgPermission
from ..repository import KgRepository
from ._common import audit_actor, authorize, version_entity


class CreateVersion:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, code: str, name: str, description: str | None
    ) -> KgVersion:
        authorize(actor, KgPermission.VERSION_CREATE)
        if await self._repository.get_version_by_code(code) is not None:
            raise KgVersionConflictError
        try:
            item = await self._repository.save_version(
                KgVersion(code=code, name=name, description=description)
            )
        except IntegrityError as exc:
            raise KgVersionConflictError from exc
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg_version.created",
            entity=version_entity(item),
            new_data={"code": item.code, "name": item.name, "description": item.description},
        )
        return item
