from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.audit.writer import TransactionalAuditWriter
from app.domains.production.batches.permissions import BatchPermission
from app.domains.production.batches.presentation import receipt_response
from app.domains.production.batches.repository import BatchRepository
from app.domains.production.batches.rules import BATCH_EDIT_WINDOW
from app.domains.production.preparation.repository import PreparationRepository
from app.shared.uow import transaction

from .commands import CreateReceipt, UpdateReceipt, VoidReceipt
from .queries import ReceiptQueries
from .repository import ReceiptRepository
from .schemas import (
    BatchReceiptListResponse,
    BatchReceiptResponse,
    CreateBatchReceiptRequest,
    UpdateBatchReceiptRequest,
    VoidBatchReceiptRequest,
)

router = APIRouter(prefix="/batches", tags=["batch"])


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


@router.get("/{batch_id}/receipts", response_model=BatchReceiptListResponse)
async def list_batch_receipts(
    batch_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    request: Request,
    include_voided: bool = False,
) -> BatchReceiptListResponse:
    async with _session_factory(request)() as session:
        receipts = await ReceiptQueries(BatchRepository(session), ReceiptRepository(session)).list(
            batch_id, include_voided=include_voided
        )
        items = [receipt_response(receipt) for receipt in receipts]
    return BatchReceiptListResponse(items=items, total=len(items))


@router.post(
    "/{batch_id}/receipts", response_model=BatchReceiptResponse, status_code=status.HTTP_201_CREATED
)
async def create_batch_receipt(
    batch_id: UUID,
    payload: CreateBatchReceiptRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.RECEIPT_CREATE))
    ],
    request: Request,
) -> BatchReceiptResponse:
    async with transaction(_session_factory(request)) as session:
        receipt = await CreateReceipt(
            BatchRepository(session),
            ReceiptRepository(session),
            PreparationRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(
            actor=principal, batch_id=batch_id, quantity=payload.quantity, comment=payload.comment
        )
        return receipt_response(receipt)


@router.patch("/{batch_id}/receipts/{receipt_id}", response_model=BatchReceiptResponse)
async def update_batch_receipt(
    batch_id: UUID,
    receipt_id: UUID,
    payload: UpdateBatchReceiptRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.RECEIPT_UPDATE))
    ],
    request: Request,
) -> BatchReceiptResponse:
    async with transaction(_session_factory(request)) as session:
        receipt = await UpdateReceipt(
            BatchRepository(session),
            ReceiptRepository(session),
            TransactionalAuditWriter.from_session(session),
            edit_window=BATCH_EDIT_WINDOW,
        ).execute(
            actor=principal,
            batch_id=batch_id,
            receipt_id=receipt_id,
            updates=payload.model_dump(exclude_unset=True),
        )
        return receipt_response(receipt)


@router.post("/{batch_id}/receipts/{receipt_id}/void", response_model=BatchReceiptResponse)
async def void_batch_receipt(
    batch_id: UUID,
    receipt_id: UUID,
    payload: VoidBatchReceiptRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.RECEIPT_VOID))
    ],
    request: Request,
) -> BatchReceiptResponse:
    async with transaction(_session_factory(request)) as session:
        receipt = await VoidReceipt(
            BatchRepository(session),
            ReceiptRepository(session),
            TransactionalAuditWriter.from_session(session),
            edit_window=BATCH_EDIT_WINDOW,
        ).execute(actor=principal, batch_id=batch_id, receipt_id=receipt_id, reason=payload.reason)
        return receipt_response(receipt)
