from secrets import token_hex
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.contexts.production.kg.commands import AllocateForBatch
from app.contexts.production.kg.repository import KgRepository
from app.contexts.production.preparation.commands.start import CreateInitialPreparation
from app.contexts.production.preparation.repository import PreparationRepository
from app.contexts.production.production_orders.queries import ProductionOrderQueries
from app.modules.batch.exceptions import BatchKgVersionArchivedError
from app.modules.kg.exceptions import KgVersionNotFoundError
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, batch_entity
from ..compat import LegacyKgUnitBridge
from ..model import Batch
from ..repository import BatchRepository
from ..rules import ensure_management_allowed


class CreateBatch:
    """Create the Batch, allocated KG rows, preparation request and audit in one UoW."""

    def __init__(
        self,
        repository: BatchRepository,
        kg_repository: KgRepository,
        kg_units: LegacyKgUnitBridge,
        preparation: PreparationRepository,
        orders: ProductionOrderQueries,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._repository = repository
        self._kg_repository = kg_repository
        self._kg_units = kg_units
        self._preparation = preparation
        self._orders = orders
        self._audit = audit

    async def execute(
        self,
        *,
        actor: CurrentPrincipal,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
        activation_type: ActivationType,
        lorawan_version: LoRaWanVersion,
        kg_version_id: UUID | None = None,
        production_order_id: UUID | None = None,
    ) -> Batch:
        ensure_management_allowed(actor)
        if production_order_id is not None:
            await self._orders.ensure_assignable(production_order_id)
        if kg_version_id is not None:
            version = await self._kg_repository.get_version(kg_version_id)
            if version is None:
                raise KgVersionNotFoundError
            if version.archived_at is not None:
                raise BatchKgVersionArchivedError
        allocation = await AllocateForBatch(self._kg_repository).execute(
            prefix=dev_eui_prefix, quantity=planned_qty
        )
        batch = await self._repository.create(
            name=name,
            description=description,
            dev_eui_prefix=allocation.prefix.prefix,
            kg_version_id=kg_version_id,
            planned_qty=planned_qty,
            day_plan_qty=day_plan_qty,
            created_by_user_id=actor.user_id,
            activation_type=activation_type,
            lorawan_version=lorawan_version,
            join_eui=token_hex(8),
            production_order_id=production_order_id,
        )
        kg_quantity = await self._kg_units.create_allocated_rows(
            dev_euis=allocation.dev_euis,
            short_code=allocation.prefix.short_code,
            batch_id=batch.id,
        )
        await CreateInitialPreparation(self._preparation).execute(batch.id)
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch.created",
            entity=batch_entity(batch),
            new_data={
                "production_order_id": str(batch.production_order_id)
                if batch.production_order_id
                else None,
                "name": batch.name,
                "description": batch.description,
                "dev_eui_prefix": allocation.prefix.prefix,
                "kg_version_id": str(kg_version_id) if kg_version_id else None,
                "dev_eui_start": allocation.dev_euis[0],
                "dev_eui_end": allocation.dev_euis[-1],
                "planned_qty": batch.planned_qty,
                "day_plan_qty": batch.day_plan_qty,
                "status": batch.status.value,
                "lorawan_config": {
                    "activation_type": activation_type.value,
                    "lorawan_version": lorawan_version.value,
                    "join_eui": batch.lorawan_config.join_eui if batch.lorawan_config else None,
                },
                "kg_quantity": kg_quantity,
            },
        )
        return batch
