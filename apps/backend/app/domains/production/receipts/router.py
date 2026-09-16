from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.production.batches.permissions import BatchPermission
from app.domains.production.batches.presentation import receipt_response
from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission
from app.shared.uow import transaction

from .schemas import (
    BatchReceiptListResponse,
    BatchReceiptResponse,
    CreateBatchReceiptRequest,
    UpdateBatchReceiptRequest,
    VoidBatchReceiptRequest,
)
from .wiring import (
    create_queries,
    create_receipt_command,
    update_receipt_command,
    void_receipt_command,
)

router = APIRouter(prefix="/batches", tags=["batch"])


@router.get("/{batch_id}/receipts", response_model=BatchReceiptListResponse)
async def list_batch_receipts(
    batch_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    session_factory: SessionFactoryDep,
    include_voided: bool = False,
) -> BatchReceiptListResponse:
    async with session_factory() as session:
        receipts = await create_queries(session).list(batch_id, include_voided=include_voided)
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
    session_factory: SessionFactoryDep,
) -> BatchReceiptResponse:
    async with transaction(session_factory) as session:
        receipt = await create_receipt_command(session).execute(
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
    session_factory: SessionFactoryDep,
) -> BatchReceiptResponse:
    async with transaction(session_factory) as session:
        receipt = await update_receipt_command(session).execute(
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
    session_factory: SessionFactoryDep,
) -> BatchReceiptResponse:
    async with transaction(session_factory) as session:
        receipt = await void_receipt_command(session).execute(
            actor=principal, batch_id=batch_id, receipt_id=receipt_id, reason=payload.reason
        )
        return receipt_response(receipt)
