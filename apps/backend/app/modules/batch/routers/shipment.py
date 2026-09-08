from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.modules.kg.schemas import DevEui

from ..permissions import BatchPermission
from ..schemas import (
    AddBatchShipmentItemRequest,
    BatchShipmentItemResponse,
    BatchShipmentListResponse,
    BatchShipmentResponse,
    CreateBatchShipmentRequest,
    UpdateBatchShipmentRequest,
    VoidBatchShipmentRequest,
)
from .common import _service, _shipment_item_response, _shipment_response

router = APIRouter(prefix="/batches", tags=["batch"])


@router.get(
    "/{batch_id}/shipments",
    response_model=BatchShipmentListResponse,
)
async def list_batch_shipments(
    batch_id: UUID,
    _: Annotated[
        CurrentPrincipalDep,
        Depends(require_permission(BatchPermission.READ)),
    ],
    request: Request,
    include_voided: bool = False,
) -> BatchShipmentListResponse:
    shipments = await _service(request).list_shipments(
        batch_id,
        include_voided=include_voided,
    )

    quantities = await _service(request).count_shipment_quantities(batch_id) if shipments else {}
    items: list[BatchShipmentResponse] = []

    for shipment in shipments:
        items.append(
            await _shipment_response(
                request,
                batch_id=batch_id,
                shipment=shipment,
                quantity=quantities.get(shipment.id, 0),
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
        Depends(require_permission(BatchPermission.SHIPMENT_CREATE)),
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
        Depends(require_permission(BatchPermission.SHIPMENT_UPDATE)),
    ],
    request: Request,
) -> BatchShipmentResponse:
    shipment = await _service(request).update_shipment(
        actor=principal,
        batch_id=batch_id,
        shipment_id=shipment_id,
        updates=payload.model_dump(exclude_unset=True),
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
        Depends(require_permission(BatchPermission.READ)),
    ],
    request: Request,
) -> list[BatchShipmentItemResponse]:
    items = await _service(request).list_shipment_items(
        batch_id=batch_id,
        shipment_id=shipment_id,
    )

    return [_shipment_item_response(item) for item in items]


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
        Depends(require_permission(BatchPermission.SHIPMENT_UPDATE)),
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
        Depends(require_permission(BatchPermission.SHIPMENT_UPDATE)),
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
        Depends(require_permission(BatchPermission.SHIPMENT_COMPLETE)),
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
        Depends(require_permission(BatchPermission.SHIPMENT_VOID)),
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
