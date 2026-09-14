"""Legacy API facade delegating receipt work to production.receipts."""

from collections.abc import Mapping
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches.repository import BatchRepository
from app.contexts.production.preparation.repository import PreparationRepository
from app.contexts.production.receipts.commands import CreateReceipt, UpdateReceipt, VoidReceipt
from app.contexts.production.receipts.model import BatchReceipt
from app.contexts.production.receipts.queries import ReceiptQueries
from app.contexts.production.receipts.repository import ReceiptRepository
from app.shared.security import CurrentPrincipal
from app.shared.uow import transaction

from .lifecycle import BATCH_EDIT_WINDOW


class ReceiptService:
    """Compatibility session runner; receipt policy is exclusively in new commands."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        edit_window: timedelta = BATCH_EDIT_WINDOW,
    ) -> None:
        self._session_factory = session_factory
        self._edit_window = edit_window

    async def list_receipts(
        self, batch_id: UUID, *, include_voided: bool = False
    ) -> list[BatchReceipt]:
        async with self._session_factory() as session:
            return await ReceiptQueries(BatchRepository(session), ReceiptRepository(session)).list(
                batch_id, include_voided=include_voided
            )

    async def get_received_total(self, batch_id: UUID) -> int:
        async with self._session_factory() as session:
            return await ReceiptQueries(
                BatchRepository(session), ReceiptRepository(session)
            ).received_total(batch_id)

    async def create_receipt(
        self, *, actor: CurrentPrincipal, batch_id: UUID, quantity: int, comment: str | None
    ) -> BatchReceipt:
        async with transaction(self._session_factory) as session:
            return await CreateReceipt(
                BatchRepository(session),
                ReceiptRepository(session),
                PreparationRepository(session),
                TransactionalAuditWriter.from_session(session),
            ).execute(actor=actor, batch_id=batch_id, quantity=quantity, comment=comment)

    async def update_receipt(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchReceipt:
        async with transaction(self._session_factory) as session:
            return await UpdateReceipt(
                BatchRepository(session),
                ReceiptRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, receipt_id=receipt_id, updates=updates)

    async def void_receipt(
        self, *, actor: CurrentPrincipal, batch_id: UUID, receipt_id: UUID, reason: str
    ) -> BatchReceipt:
        async with transaction(self._session_factory) as session:
            return await VoidReceipt(
                BatchRepository(session),
                ReceiptRepository(session),
                TransactionalAuditWriter.from_session(session),
                edit_window=self._edit_window,
            ).execute(actor=actor, batch_id=batch_id, receipt_id=receipt_id, reason=reason)
