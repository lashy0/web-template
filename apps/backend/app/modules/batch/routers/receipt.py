from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission

from ..permissions import BatchPermission
from ..schemas import (
    BatchReceiptListResponse,
    BatchReceiptResponse,
    CreateBatchReceiptRequest,
    UpdateBatchReceiptRequest,
    VoidBatchReceiptRequest,
)
from .common import _receipt_response, _service

router = APIRouter(prefix="/batches", tags=["batch"])


@router.get("/{batch_id}/receipts", response_model=BatchReceiptListResponse)
async def list_batch_receipts(
    batch_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.READ)),
    ],
    request: Request,
    include_voided: bool = False,
) -> BatchReceiptListResponse:
    receipts = await _service(request).list_receipts(
        batch_id,
        include_voided=include_voided,
    )

    return BatchReceiptListResponse(
        items=[_receipt_response(receipt) for receipt in receipts],
        total=len(receipts),
    )


@router.post(
    "/{batch_id}/receipts",
    response_model=BatchReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_receipt(
    batch_id: UUID,
    payload: CreateBatchReceiptRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.RECEIPT_CREATE)),
    ],
    request: Request,
) -> BatchReceiptResponse:
    receipt = await _service(request).create_receipt(
        actor=principal,
        batch_id=batch_id,
        quantity=payload.quantity,
        comment=payload.comment,
    )

    return _receipt_response(receipt)


@router.patch(
    "/{batch_id}/receipts/{receipt_id}",
    response_model=BatchReceiptResponse,
)
async def update_batch_receipt(
    batch_id: UUID,
    receipt_id: UUID,
    payload: UpdateBatchReceiptRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.RECEIPT_UPDATE)),
    ],
    request: Request,
) -> BatchReceiptResponse:
    receipt = await _service(request).update_receipt(
        actor=principal,
        batch_id=batch_id,
        receipt_id=receipt_id,
        updates=payload.model_dump(exclude_unset=True),
    )

    return _receipt_response(receipt)


@router.post(
    "/{batch_id}/receipts/{receipt_id}/void",
    response_model=BatchReceiptResponse,
)
async def void_batch_receipt(
    batch_id: UUID,
    receipt_id: UUID,
    payload: VoidBatchReceiptRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.RECEIPT_VOID)),
    ],
    request: Request,
) -> BatchReceiptResponse:
    receipt = await _service(request).void_receipt(
        actor=principal,
        batch_id=batch_id,
        receipt_id=receipt_id,
        reason=payload.reason,
    )

    return _receipt_response(receipt)
