from sqlalchemy.exc import IntegrityError

from app.audit.writer import TransactionalAuditWriter
from app.modules.kg.exceptions import KgDevEuiPrefixConflictError
from app.modules.kg.permissions import KgPermission
from app.shared.security import CurrentPrincipal

from ..model import KgDevEuiPrefix
from ..repository import KgRepository
from ._common import audit_actor, authorize, prefix_entity


class CreatePrefix:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, prefix: str, short_code: str, name: str | None
    ) -> KgDevEuiPrefix:
        authorize(actor, KgPermission.PREFIX_CREATE)
        if (
            await self._repository.get_prefix(prefix) is not None
            or await self._repository.get_prefix_by_short_code(short_code) is not None
        ):
            raise KgDevEuiPrefixConflictError
        item = KgDevEuiPrefix(prefix=prefix, short_code=short_code, name=name)
        try:
            item = await self._repository.save_prefix(item)
        except IntegrityError as exc:
            raise KgDevEuiPrefixConflictError from exc
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg_prefix.created",
            entity=prefix_entity(item),
            new_data={"prefix": item.prefix, "short_code": item.short_code, "name": item.name},
        )
        return item
