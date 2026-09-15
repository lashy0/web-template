from app.audit.types import AuditEntity
from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches.contracts import VerificationHistoryPort
from app.shared.security import CurrentPrincipal

from ..exceptions import KgCannotBeDeletedError, KgNotFoundError
from ..model import KgState, KgUnit
from ..repository import KgRepository
from ._common import audit_actor


class DeleteKg:
    def __init__(
        self,
        repository: KgRepository,
        verification_history: VerificationHistoryPort,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._repository = repository
        self._verification_history = verification_history
        self._audit = audit

    async def execute(self, *, actor: CurrentPrincipal, dev_eui: str) -> None:
        kg = await self._repository.get_by_dev_eui(dev_eui, for_update=True)
        if kg is None:
            raise KgNotFoundError
        if (
            kg.state is not KgState.REGISTERED
            or await self._verification_history.has_history_for_kg(kg.dev_eui)
        ):
            raise KgCannotBeDeletedError
        await self._audit.record(
            actor=audit_actor(actor),
            action="kg.deleted",
            entity=_entity(kg),
            old_data={"dev_eui": kg.dev_eui, "batch_id": str(kg.batch_id), "state": kg.state.value},
        )
        await self._repository.delete_unit(kg)


def _entity(kg: KgUnit) -> AuditEntity:

    return AuditEntity(type="kg", id=kg.dev_eui, display_name=kg.dev_eui, identifier=kg.dev_eui)
