from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService

from ..models import BatchReceipt
from ..repositories import BatchReceiptRepository, BatchRepository
from . import audit, lifecycle, queries
from .lifecycle import BATCH_EDIT_WINDOW
from .transactions import transaction


class ReceiptService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window

    async def list_receipts(
        self,
        batch_id: UUID,
        *,
        include_voided: bool = False,
    ) -> list[BatchReceipt]:
        async with self._session_factory() as session:
            await queries.required_batch(
                BatchRepository(session),
                batch_id,
            )

            return await BatchReceiptRepository(session).list_by_batch(
                batch_id,
                include_voided=include_voided,
            )

    async def get_received_total(self, batch_id: UUID) -> int:
        async with self._session_factory() as session:
            await queries.required_batch(
                BatchRepository(session),
                batch_id,
            )

            return await BatchReceiptRepository(session).get_total(batch_id)

    async def create_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        quantity: int,
        comment: str | None,
    ) -> BatchReceipt:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )

            lifecycle.ensure_in_production(batch)

            receipt = await BatchReceiptRepository(session).create(
                batch_id=batch.id,
                quantity=quantity,
                comment=comment,
                created_by_user_id=actor.user_id,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch_receipt.created",
                entity=audit.receipt_entity(receipt),
                new_data={
                    "batch_id": str(batch.id),
                    "quantity": receipt.quantity,
                    "comment": receipt.comment,
                },
            )

            return receipt

    async def update_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchReceipt:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )
            lifecycle.ensure_not_archived(batch)

            repository = BatchReceiptRepository(session)
            receipt = await queries.required_receipt(
                repository,
                receipt_id,
                batch_id=batch.id,
            )

            lifecycle.ensure_receipt_active(receipt)
            lifecycle.ensure_receipt_edit_allowed(
                receipt,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            if not updates:
                return receipt

            old_values = {field: getattr(receipt, field) for field in updates}

            receipt = await repository.update_details(
                receipt,
                updates=updates,
            )

            new_values = {field: getattr(receipt, field) for field in updates}

            changed = {
                field: value for field, value in new_values.items() if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=audit.audit_actor(actor),
                    action="batch_receipt.updated",
                    entity=audit.receipt_entity(receipt),
                    old_data={field: old_values[field] for field in changed},
                    new_data=changed,
                )

            return receipt

    async def void_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        reason: str,
    ) -> BatchReceipt:
        lifecycle.ensure_management_allowed(actor)

        async with transaction(self._session_factory) as session:
            batch = await queries.required_batch(
                BatchRepository(session),
                batch_id,
                for_update=True,
            )
            lifecycle.ensure_not_archived(batch)

            repository = BatchReceiptRepository(session)
            receipt = await queries.required_receipt(
                repository,
                receipt_id,
                batch_id=batch.id,
            )

            lifecycle.ensure_receipt_active(receipt)
            lifecycle.ensure_receipt_edit_allowed(
                receipt,
                actor=actor,
                now=datetime.now(UTC),
                edit_window=self._edit_window,
            )

            voided_at = datetime.now(UTC)

            receipt = await repository.void(
                receipt,
                voided_at=voided_at,
                reason=reason,
            )

            await AuditService.from_session(session).record(
                actor=audit.audit_actor(actor),
                action="batch_receipt.voided",
                entity=audit.receipt_entity(receipt),
                old_data={
                    "voided_at": None,
                    "void_reason": None,
                },
                new_data={
                    "voided_at": voided_at.isoformat(),
                    "void_reason": reason,
                },
            )

            return receipt
