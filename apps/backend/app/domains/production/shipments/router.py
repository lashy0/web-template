from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domains.production.batches.permissions import BatchPermission
from app.domains.production.batches.presentation import shipment_item_response, shipment_response
from app.domains.production.kg.schemas import DevEui
from app.shared.dependencies import SessionFactoryDep
from app.shared.security.dependencies import CurrentPrincipalDep, require_permission
from app.shared.uow import transaction

from .schemas import (
    AddBatchShipmentItemRequest,
    BatchShipmentItemResponse,
    BatchShipmentListResponse,
    BatchShipmentResponse,
    CreateBatchShipmentRequest,
    UpdateBatchShipmentRequest,
    VoidBatchShipmentRequest,
)
from .wiring import (
    add_shipment_item_command,
    complete_shipment_command,
    create_queries,
    create_shipment_command,
    remove_shipment_item_command,
    shipment_item_count,
    update_shipment_command,
    void_shipment_command,
)

router = APIRouter(prefix="/batches", tags=["batch"])


@router.get("/{batch_id}/shipments", response_model=BatchShipmentListResponse)
async def list_batch_shipments(
    batch_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    session_factory: SessionFactoryDep,
    include_voided: bool = False,
) -> BatchShipmentListResponse:
    async with session_factory() as session:
        queries = create_queries(session)
        shipments = await queries.list_by_batch(batch_id, include_voided=include_voided)
        quantities = await queries.item_counts(batch_id) if shipments else {}
        items = [
            shipment_response(shipment, quantity=quantities.get(shipment.id, 0))
            for shipment in shipments
        ]
    return BatchShipmentListResponse(items=items, total=len(items))


@router.post(
    "/{batch_id}/shipments",
    response_model=BatchShipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_shipment(
    batch_id: UUID,
    payload: CreateBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_CREATE))
    ],
    session_factory: SessionFactoryDep,
) -> BatchShipmentResponse:
    async with transaction(session_factory) as session:
        shipment = await create_shipment_command(session).execute(
            actor=principal, batch_id=batch_id, comment=payload.comment
        )
        return shipment_response(shipment, quantity=0)


@router.patch("/{batch_id}/shipments/{shipment_id}", response_model=BatchShipmentResponse)
async def update_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    payload: UpdateBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_UPDATE))
    ],
    session_factory: SessionFactoryDep,
) -> BatchShipmentResponse:
    async with transaction(session_factory) as session:
        shipment = await update_shipment_command(session).execute(
            actor=principal,
            batch_id=batch_id,
            shipment_id=shipment_id,
            updates=payload.model_dump(exclude_unset=True),
        )
        return shipment_response(shipment, quantity=await shipment_item_count(session, shipment.id))


@router.get(
    "/{batch_id}/shipments/{shipment_id}/items", response_model=list[BatchShipmentItemResponse]
)
async def list_batch_shipment_items(
    batch_id: UUID,
    shipment_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    session_factory: SessionFactoryDep,
) -> list[BatchShipmentItemResponse]:
    async with session_factory() as session:
        items = await create_queries(session).list_items(batch_id=batch_id, shipment_id=shipment_id)
        return [shipment_item_response(item) for item in items]


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
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_UPDATE))
    ],
    session_factory: SessionFactoryDep,
) -> BatchShipmentItemResponse:
    async with transaction(session_factory) as session:
        item = await add_shipment_item_command(session).execute(
            actor=principal, batch_id=batch_id, shipment_id=shipment_id, dev_eui=payload.dev_eui
        )
        return shipment_item_response(item)


@router.delete(
    "/{batch_id}/shipments/{shipment_id}/items/{dev_eui}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_batch_shipment_item(
    batch_id: UUID,
    shipment_id: UUID,
    dev_eui: DevEui,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_UPDATE))
    ],
    session_factory: SessionFactoryDep,
) -> None:
    async with transaction(session_factory) as session:
        await remove_shipment_item_command(session).execute(
            actor=principal, batch_id=batch_id, shipment_id=shipment_id, dev_eui=dev_eui
        )


@router.post("/{batch_id}/shipments/{shipment_id}/complete", response_model=BatchShipmentResponse)
async def complete_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_COMPLETE))
    ],
    session_factory: SessionFactoryDep,
) -> BatchShipmentResponse:
    async with transaction(session_factory) as session:
        shipment = await complete_shipment_command(session).execute(
            actor=principal, batch_id=batch_id, shipment_id=shipment_id
        )
        return shipment_response(shipment, quantity=await shipment_item_count(session, shipment.id))


@router.post("/{batch_id}/shipments/{shipment_id}/void", response_model=BatchShipmentResponse)
async def void_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    payload: VoidBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_VOID))
    ],
    session_factory: SessionFactoryDep,
) -> BatchShipmentResponse:
    async with transaction(session_factory) as session:
        shipment = await void_shipment_command(session).execute(
            actor=principal, batch_id=batch_id, shipment_id=shipment_id, reason=payload.reason
        )
        return shipment_response(shipment, quantity=await shipment_item_count(session, shipment.id))
