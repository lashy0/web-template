from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.kg.exceptions import KgVersionNotFoundError
from app.modules.kg.repositories import KgVersionRepository
from app.modules.kg.services import KgPrefixService, KgService
from app.modules.verification.services import VerificationManagementService

from ..exceptions import BatchCannotBeDeletedError, BatchKgVersionArchivedError
from ..models import Batch, BatchStatus
from ..repositories import (
    BatchReceiptRepository,
    BatchRepository,
    BatchShipmentRepository,
)
from . import audit, lifecycle, queries
from .lifecycle import BATCH_EDIT_WINDOW
from .transactions import transaction


class BatchService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window

    async def get(self, batch_id: UUID) -> Batch | None:
        async with self._session_factory() as session:
            return await BatchRepository(session).get_by_id(batch_id)

    async def list(
        self,
        *,
        q: str | None,
        status: BatchStatus | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[Batch], int]:
        async with self._session_factory() as session:
            return await BatchRepository(session).search(
                q=q,
                status=status,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        name: str,
        description: str | None,
        dev_eui_prefix: str,
        planned_qty: int,
        day_plan_qty: int,
        kg_version_id: UUID | None = None,
    ) -> Batch:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch_repository = BatchRepository(session)
            kg_operations = KgService(session)

            if kg_version_id is not None:
                version = await KgVersionRepository(session).get(kg_version_id)

                if version is None:
                    raise KgVersionNotFoundError

                if version.archived_at is not None:
                    raise BatchKgVersionArchivedError

            prefix, dev_euis = await KgPrefixService(session).prepare_allocation(
                dev_eui_prefix, planned_qty
            )

            if kg_version_id is None:
                batch = await batch_repository.create(
                    name=name,
                    description=description,
                    dev_eui_prefix=prefix.prefix,
                    planned_qty=planned_qty,
                    day_plan_qty=day_plan_qty,
                    created_by_user_id=actor.user_id,
                )

            else:
                batch = await batch_repository.create(
                    name=name,
                    description=description,
                    dev_eui_prefix=prefix.prefix,
                    kg_version_id=kg_version_id,
                    planned_qty=planned_qty,
                    day_plan_qty=day_plan_qty,
                    created_by_user_id=actor.user_id,
                )

            kg_units = await kg_operations.allocate_for_batch(
                dev_euis=dev_euis,
                short_code=prefix.short_code,
                batch_id=batch.id,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch.created",
                entity=audit.batch_entity(batch),
                new_data={
                    "name": batch.name,
                    "description": batch.description,
                    "dev_eui_prefix": prefix.prefix,
                    "kg_version_id": str(kg_version_id) if kg_version_id else None,
                    "dev_eui_start": dev_euis[0],
                    "dev_eui_end": dev_euis[-1],
                    "planned_qty": batch.planned_qty,
                    "day_plan_qty": batch.day_plan_qty,
                    "status": batch.status.value,
                    "kg_quantity": len(kg_units),
                },
            )

            return batch

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        updates: Mapping[str, object],
    ) -> Batch:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            repository = BatchRepository(session)
            batch = await queries.required_batch(repository, batch_id, for_update=True)

            lifecycle.ensure_not_archived(batch)
            lifecycle.ensure_batch_edit_allowed(
                batch,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            if not updates:
                return batch

            old_values = {field: getattr(batch, field) for field in updates}

            batch = await repository.update_details(
                batch,
                updates=updates,
            )

            new_values = {field: getattr(batch, field) for field in updates}

            changed = {
                field: value for field, value in new_values.items() if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=audit.audit_actor(actor),
                    action="batch.updated",
                    entity=audit.batch_entity(batch),
                    old_data={field: old_values[field] for field in changed},
                    new_data=changed,
                )

            return batch

    async def complete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> Batch:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            repository = BatchRepository(session)
            batch = await queries.required_batch(repository, batch_id, for_update=True)

            lifecycle.ensure_in_production(batch)

            old_status = batch.status
            completed_at = datetime.now(UTC)

            batch = await repository.update_completed(
                batch,
                completed_at=completed_at,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch.completed",
                entity=audit.batch_entity(batch),
                old_data={
                    "status": old_status.value,
                    "completed_at": None,
                },
                new_data={
                    "status": batch.status.value,
                    "completed_at": completed_at.isoformat(),
                },
            )

            return batch

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        archived: bool,
    ) -> Batch:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            repository = BatchRepository(session)
            batch = await queries.required_batch(repository, batch_id, for_update=True)

            if archived:
                if batch.archived_at is not None:
                    return batch

                archived_at = datetime.now(UTC)

                batch = await repository.update_archived(
                    batch,
                    archived_at=archived_at,
                )

                action = "batch.archived"
                old_data: dict[str, str | None] = {
                    "archived_at": None,
                }

                new_data: dict[str, str | None] = {
                    "archived_at": archived_at.isoformat(),
                }

            else:
                if batch.archived_at is None:
                    return batch

                old_archived_at = batch.archived_at

                batch = await repository.update_archived(
                    batch,
                    archived_at=None,
                )

                action = "batch.restored"
                old_data = {
                    "archived_at": old_archived_at.isoformat(),
                }

                new_data = {
                    "archived_at": None,
                }

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action=action,
                entity=audit.batch_entity(batch),
                old_data=old_data,
                new_data=new_data,
            )

            return batch

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
    ) -> None:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch_repository = BatchRepository(session)
            receipt_repository = BatchReceiptRepository(session)
            shipment_repository = BatchShipmentRepository(session)
            kg_operations = KgService(session)

            batch = await queries.required_batch(
                batch_repository,
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_not_archived(batch)
            lifecycle.ensure_batch_edit_allowed(
                batch,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            if batch.status != BatchStatus.IN_PRODUCTION:
                raise BatchCannotBeDeletedError

            if await receipt_repository.exists_by_batch(batch.id):
                raise BatchCannotBeDeletedError

            if await shipment_repository.exists_by_batch(batch.id):
                raise BatchCannotBeDeletedError

            if await kg_operations.has_production_activity(batch.id):
                raise BatchCannotBeDeletedError

            if await VerificationManagementService.has_batch_history(session, batch.id):
                raise BatchCannotBeDeletedError

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch.deleted",
                entity=audit.batch_entity(batch),
                old_data={
                    "name": batch.name,
                    "description": batch.description,
                    "planned_qty": batch.planned_qty,
                    "day_plan_qty": batch.day_plan_qty,
                    "status": batch.status.value,
                },
            )

            await kg_operations.delete_registered_for_batch(batch.id)
            await batch_repository.delete(batch)
