from app.audit.writer import TransactionalAuditWriter
from app.modules.audit.types import AuditEntity
from app.shared.security import CurrentPrincipal

from ..exceptions import KgNotFoundError
from ..model import KgState, KgUnit
from ..repository import KgRepository
from ._common import audit_actor


class SetKgState:
    def __init__(self, repository: KgRepository, audit: TransactionalAuditWriter) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(self, *, actor: CurrentPrincipal, dev_eui: str, state: KgState) -> KgUnit:
        kg = await self._repository.get_by_dev_eui(dev_eui, for_update=True)
        if kg is None:
            raise KgNotFoundError
        if kg.state is state:
            return kg
        old_state = kg.state
        kg = await self._repository.update_state(kg, state=state)
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg.state_changed",
            entity=_entity(kg),
            old_data={"state": old_state.value},
            new_data={"state": kg.state.value},
        )
        return kg


def _entity(kg: KgUnit) -> AuditEntity:

    return AuditEntity(type="kg", id=kg.dev_eui, display_name=kg.dev_eui, identifier=kg.dev_eui)
