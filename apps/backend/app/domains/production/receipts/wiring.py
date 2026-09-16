from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.domains.production.batches.repository import BatchRepository
from app.domains.production.batches.rules import BATCH_EDIT_WINDOW
from app.domains.production.preparation.repository import PreparationRepository

from .commands import CreateReceipt, UpdateReceipt, VoidReceipt
from .queries import ReceiptQueries
from .repository import ReceiptRepository


def create_queries(session: AsyncSession) -> ReceiptQueries:
    return ReceiptQueries(BatchRepository(session), ReceiptRepository(session))


def create_receipt_command(session: AsyncSession) -> CreateReceipt:
    return CreateReceipt(
        BatchRepository(session),
        ReceiptRepository(session),
        PreparationRepository(session),
        TransactionalAuditWriter.from_session(session),
    )


def update_receipt_command(session: AsyncSession) -> UpdateReceipt:
    return UpdateReceipt(
        BatchRepository(session),
        ReceiptRepository(session),
        TransactionalAuditWriter.from_session(session),
        edit_window=BATCH_EDIT_WINDOW,
    )


def void_receipt_command(session: AsyncSession) -> VoidReceipt:
    return VoidReceipt(
        BatchRepository(session),
        ReceiptRepository(session),
        TransactionalAuditWriter.from_session(session),
        edit_window=BATCH_EDIT_WINDOW,
    )
