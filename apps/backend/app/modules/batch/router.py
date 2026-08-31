from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.batch.exceptions import BatchNotFoundError
from app.modules.batch.models import (
    Batch,
    BatchReceipt,
    BatchShipment,
    BatchShipmentItem,
    BatchStatus,
)
from app.modules.batch.permissions import BatchPermission
from app.modules.batch.schemas import (
    AddBatchShipmentItemRequest,
    BatchListResponse,
    BatchReceiptListResponse,
    BatchReceiptResponse,
    BatchResponse,
    BatchShipmentItemResponse,
    BatchShipmentListResponse,
    BatchShipmentResponse,
    CreateBatchReceiptRequest,
    CreateBatchRequest,
    CreateBatchShipmentRequest,
    UpdateBatchArchivedRequest,
    UpdateBatchReceiptRequest,
    UpdateBatchRequest,
    UpdateBatchShipmentRequest,
    VoidBatchReceiptRequest,
    VoidBatchShipmentRequest,
)
from app.modules.batch.service import BatchManagementService
from app.modules.kg.schemas import DevEui

router = APIRouter(prefix="/batches", tags=["batch"])


def _service(request: Request) -> BatchManagementService:
    return cast(BatchManagementService, request.app.state.batch_management)


def _batch_response(batch: Batch) -> BatchResponse:
    return BatchResponse(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        dev_eui_prefix=batch.dev_eui_prefix,
        planned_qty=batch.planned_qty,
        day_plan_qty=batch.day_plan_qty,
        status=batch.status,
        created_by_user_id=batch.created_by_user_id,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        completed_at=batch.completed_at,
        archived_at=batch.archived_at,
    )


def _receipt_response(receipt: BatchReceipt) -> BatchReceiptResponse:
    return BatchReceiptResponse(
        id=receipt.id,
        batch_id=receipt.batch_id,
        quantity=receipt.quantity,
        comment=receipt.comment,
        created_by_user_id=receipt.created_by_user_id,
        created_at=receipt.created_at,
        updated_at=receipt.updated_at,
        voided_at=receipt.voided_at,
        void_reason=receipt.void_reason,
    )


def _shipment_item_response(item: BatchShipmentItem) -> BatchShipmentItemResponse:
    return BatchShipmentItemResponse(
        shipment_id=item.shipment_id,
        kg_dev_eui=item.kg_dev_eui,
        created_at=item.created_at,
    )


async def _shipment_response(
    request: Request,
    *,
    batch_id: UUID,
    shipment: BatchShipment,
) -> BatchShipmentResponse:
    quantity = await _service(request).count_shipment_items(
        batch_id=batch_id,
        shipment_id=shipment.id,
    )

    return BatchShipmentResponse(
        id=shipment.id,
        batch_id=shipment.batch_id,
        comment=shipment.comment,
        quantity=quantity,
        created_by_user_id=shipment.created_by_user_id,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
        completed_at=shipment.completed_at,
        voided_at=shipment.voided_at,
        void_reason=shipment.void_reason,
    )


# Batch

@router.get("/", response_model=BatchListResponse)
async def list_batches(
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.READ)),
    ],
    request: Request,
    q: str | None = None,
    status_filter: BatchStatus | None = Query(default=None, alias="status"),
    archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal[
        "name",
        "planned_qty",
        "day_plan_qty",
        "status",
        "created_at",
        "updated_at",
        "completed_at",
        "archived_at",
    ] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> BatchListResponse:
    batches, total = await _service(request).list(
        q=q,
        status=status_filter,
        archived=archived,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )

    return BatchListResponse(
        items=[
            _batch_response(batch)
            for batch in batches
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.READ)),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).get(batch_id)

    if batch is None:
        raise BatchNotFoundError

    return _batch_response(batch)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: CreateBatchRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.CREATE
            )
        ),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).create(
        actor=principal,
        name=payload.name,
        description=payload.description,
        dev_eui_prefix=payload.dev_eui_prefix,
        planned_qty=payload.planned_qty,
        day_plan_qty=payload.day_plan_qty,
    )

    return _batch_response(batch)


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    payload: UpdateBatchRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.UPDATE
            )
        ),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).update(
        actor=principal,
        batch_id=batch_id,
        updates=payload.model_dump(
            exclude_unset=True
        ),
    )

    return _batch_response(batch)


@router.put("/{batch_id}/archived", response_model=BatchResponse)
async def update_batch_archived(
    batch_id: UUID,
    payload: UpdateBatchArchivedRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.ARCHIVE
            )
        ),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).set_archived(
        actor=principal,
        batch_id=batch_id,
        archived=payload.archived,
    )

    return _batch_response(batch)


@router.post("/{batch_id}/complete", response_model=BatchResponse)
async def complete_batch(
    batch_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.COMPLETE
            )
        ),
    ],
    request: Request,
) -> BatchResponse:
    batch = await _service(request).complete(
        actor=principal,
        batch_id=batch_id,
    )

    return _batch_response(batch)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.DELETE
            )
        ),
    ],
    request: Request,
) -> None:
    await _service(request).delete(
        actor=principal,
        batch_id=batch_id,
    )


# Receipts

@router.get("/{batch_id}/receipts", response_model=BatchReceiptListResponse)
async def list_batch_receipts(
    batch_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.READ
            )
        ),
    ],
    request: Request,
    include_voided: bool = False,
) -> BatchReceiptListResponse:
    receipts = await _service(request).list_receipts(
        batch_id,
        include_voided=include_voided,
    )

    return BatchReceiptListResponse(
        items=[
            _receipt_response(receipt)
            for receipt in receipts
        ],
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
        Depends(
            require_permission(
                BatchPermission.RECEIPT_CREATE
            )
        ),
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
        Depends(
            require_permission(
                BatchPermission.RECEIPT_UPDATE
            )
        ),
    ],
    request: Request,
) -> BatchReceiptResponse:
    receipt = await _service(request).update_receipt(
        actor=principal,
        batch_id=batch_id,
        receipt_id=receipt_id,
        updates=payload.model_dump(
            exclude_unset=True
        ),
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
        Depends(
            require_permission(
                BatchPermission.RECEIPT_VOID
            )
        ),
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


# Shipments

@router.get(
    "/{batch_id}/shipments",
    response_model=BatchShipmentListResponse,
)
async def list_batch_shipments(
    batch_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.READ
            )
        ),
    ],
    request: Request,
    include_voided: bool = False,
) -> BatchShipmentListResponse:
    shipments = await _service(request).list_shipments(
        batch_id,
        include_voided=include_voided,
    )

    items: list[BatchShipmentResponse] = []

    for shipment in shipments:
        items.append(
            await _shipment_response(
                request,
                batch_id=batch_id,
                shipment=shipment,
            )
        )

    return BatchShipmentListResponse(
        items=items,
        total=len(items),
    )


@router.post(
    "/{batch_id}/shipments",
    response_model=BatchShipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_shipment(
    batch_id: UUID,
    payload: CreateBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.SHIPMENT_CREATE
            )
        ),
    ],
    request: Request,
) -> BatchShipmentResponse:
    shipment = await _service(request).create_shipment(
        actor=principal,
        batch_id=batch_id,
        comment=payload.comment,
    )

    return await _shipment_response(
        request,
        batch_id=batch_id,
        shipment=shipment,
    )


@router.patch(
    "/{batch_id}/shipments/{shipment_id}",
    response_model=BatchShipmentResponse,
)
async def update_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    payload: UpdateBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.SHIPMENT_UPDATE
            )
        ),
    ],
    request: Request,
) -> BatchShipmentResponse:
    shipment = await _service(request).update_shipment(
        actor=principal,
        batch_id=batch_id,
        shipment_id=shipment_id,
        updates=payload.model_dump(
            exclude_unset=True
        ),
    )

    return await _shipment_response(
        request,
        batch_id=batch_id,
        shipment=shipment,
    )


@router.get(
    "/{batch_id}/shipments/{shipment_id}/items",
    response_model=list[BatchShipmentItemResponse],
)
async def list_batch_shipment_items(
    batch_id: UUID,
    shipment_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.READ
            )
        ),
    ],
    request: Request,
) -> list[BatchShipmentItemResponse]:
    items = await _service(request).list_shipment_items(
        batch_id=batch_id,
        shipment_id=shipment_id,
    )

    return [
        _shipment_item_response(item)
        for item in items
    ]


@router.post(
    "/{batch_id}/shipments/{shipment_id}/items",
    response_model=BatchShipmentItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_batch_shipment_item(
    batch_id: UUID,
    shipment_id: UUID,
    payload: AddBatchShipmentItemRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.SHIPMENT_UPDATE
            )
        ),
    ],
    request: Request,
) -> BatchShipmentItemResponse:
    item = await _service(request).add_shipment_item(
        actor=principal,
        batch_id=batch_id,
        shipment_id=shipment_id,
        dev_eui=payload.dev_eui,
    )

    return _shipment_item_response(item)


@router.delete(
    "/{batch_id}/shipments/{shipment_id}/items/{dev_eui}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_batch_shipment_item(
    batch_id: UUID,
    shipment_id: UUID,
    dev_eui: DevEui,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.SHIPMENT_UPDATE
            )
        ),
    ],
    request: Request,
) -> None:
    await _service(request).remove_shipment_item(
        actor=principal,
        batch_id=batch_id,
        shipment_id=shipment_id,
        dev_eui=dev_eui,
    )


@router.post(
    "/{batch_id}/shipments/{shipment_id}/complete",
    response_model=BatchShipmentResponse,
)
async def complete_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.SHIPMENT_COMPLETE
            )
        ),
    ],
    request: Request,
) -> BatchShipmentResponse:
    shipment = await _service(request).complete_shipment(
        actor=principal,
        batch_id=batch_id,
        shipment_id=shipment_id,
    )

    return await _shipment_response(
        request,
        batch_id=batch_id,
        shipment=shipment,
    )


@router.post(
    "/{batch_id}/shipments/{shipment_id}/void",
    response_model=BatchShipmentResponse,
)
async def void_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    payload: VoidBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep,
        Depends(
            require_permission(
                BatchPermission.SHIPMENT_VOID
            )
        ),
    ],
    request: Request,
) -> BatchShipmentResponse:
    shipment = await _service(request).void_shipment(
        actor=principal,
        batch_id=batch_id,
        shipment_id=shipment_id,
        reason=payload.reason,
    )

    return await _shipment_response(
        request,
        batch_id=batch_id,
        shipment=shipment,
    )
