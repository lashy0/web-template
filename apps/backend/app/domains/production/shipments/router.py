from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.audit.writer import TransactionalAuditWriter
from app.domains.production.batches.permissions import BatchPermission
from app.domains.production.batches.presentation import shipment_item_response, shipment_response
from app.domains.production.batches.repository import BatchRepository
from app.domains.production.batches.rules import BATCH_EDIT_WINDOW
from app.domains.production.kg.repository import KgRepository
from app.domains.production.kg.schemas import DevEui
from app.domains.production.preparation.repository import PreparationRepository
from app.shared.uow import transaction

from .commands import (
    AddShipmentItem,
    CompleteShipment,
    CreateShipment,
    RemoveShipmentItem,
    UpdateShipment,
    VoidShipment,
)
from .queries import ShipmentQueries
from .repository import ShipmentRepository
from .schemas import (
    AddBatchShipmentItemRequest,
    BatchShipmentItemResponse,
    BatchShipmentListResponse,
    BatchShipmentResponse,
    CreateBatchShipmentRequest,
    UpdateBatchShipmentRequest,
    VoidBatchShipmentRequest,
)

router = APIRouter(prefix="/batches", tags=["batch"])


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.database.session_factory)


@router.get("/{batch_id}/shipments", response_model=BatchShipmentListResponse)
async def list_batch_shipments(
    batch_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    request: Request,
    include_voided: bool = False,
) -> BatchShipmentListResponse:
    async with _session_factory(request)() as session:
        queries = ShipmentQueries(BatchRepository(session), ShipmentRepository(session))
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
    request: Request,
) -> BatchShipmentResponse:
    async with transaction(_session_factory(request)) as session:
        shipment = await CreateShipment(
            BatchRepository(session),
            ShipmentRepository(session),
            PreparationRepository(session),
            TransactionalAuditWriter.from_session(session),
        ).execute(actor=principal, batch_id=batch_id, comment=payload.comment)
        return shipment_response(shipment, quantity=0)


@router.patch("/{batch_id}/shipments/{shipment_id}", response_model=BatchShipmentResponse)
async def update_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    payload: UpdateBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_UPDATE))
    ],
    request: Request,
) -> BatchShipmentResponse:
    async with transaction(_session_factory(request)) as session:
        shipments = ShipmentRepository(session)
        shipment = await UpdateShipment(
            BatchRepository(session),
            shipments,
            TransactionalAuditWriter.from_session(session),
            edit_window=BATCH_EDIT_WINDOW,
        ).execute(
            actor=principal,
            batch_id=batch_id,
            shipment_id=shipment_id,
            updates=payload.model_dump(exclude_unset=True),
        )
        quantity = await shipments.item_count(shipment.id)
        return shipment_response(shipment, quantity=quantity)


@router.get(
    "/{batch_id}/shipments/{shipment_id}/items", response_model=list[BatchShipmentItemResponse]
)
async def list_batch_shipment_items(
    batch_id: UUID,
    shipment_id: UUID,
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(BatchPermission.READ))],
    request: Request,
) -> list[BatchShipmentItemResponse]:
    async with _session_factory(request)() as session:
        items = await ShipmentQueries(
            BatchRepository(session), ShipmentRepository(session)
        ).list_items(batch_id=batch_id, shipment_id=shipment_id)
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
    request: Request,
) -> BatchShipmentItemResponse:
    async with transaction(_session_factory(request)) as session:
        item = await AddShipmentItem(
            BatchRepository(session),
            ShipmentRepository(session),
            KgRepository(session),
            PreparationRepository(session),
            TransactionalAuditWriter.from_session(session),
            edit_window=BATCH_EDIT_WINDOW,
        ).execute(
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
    request: Request,
) -> None:
    async with transaction(_session_factory(request)) as session:
        await RemoveShipmentItem(
            BatchRepository(session),
            ShipmentRepository(session),
            TransactionalAuditWriter.from_session(session),
            edit_window=BATCH_EDIT_WINDOW,
        ).execute(actor=principal, batch_id=batch_id, shipment_id=shipment_id, dev_eui=dev_eui)


@router.post("/{batch_id}/shipments/{shipment_id}/complete", response_model=BatchShipmentResponse)
async def complete_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_COMPLETE))
    ],
    request: Request,
) -> BatchShipmentResponse:
    async with transaction(_session_factory(request)) as session:
        shipments = ShipmentRepository(session)
        shipment = await CompleteShipment(
            BatchRepository(session),
            shipments,
            PreparationRepository(session),
            TransactionalAuditWriter.from_session(session),
            edit_window=BATCH_EDIT_WINDOW,
        ).execute(actor=principal, batch_id=batch_id, shipment_id=shipment_id)
        return shipment_response(shipment, quantity=await shipments.item_count(shipment.id))


@router.post("/{batch_id}/shipments/{shipment_id}/void", response_model=BatchShipmentResponse)
async def void_batch_shipment(
    batch_id: UUID,
    shipment_id: UUID,
    payload: VoidBatchShipmentRequest,
    principal: Annotated[
        CurrentPrincipalDep, Depends(require_permission(BatchPermission.SHIPMENT_VOID))
    ],
    request: Request,
) -> BatchShipmentResponse:
    async with transaction(_session_factory(request)) as session:
        shipments = ShipmentRepository(session)
        shipment = await VoidShipment(
            BatchRepository(session),
            shipments,
            TransactionalAuditWriter.from_session(session),
            edit_window=BATCH_EDIT_WINDOW,
        ).execute(
            actor=principal, batch_id=batch_id, shipment_id=shipment_id, reason=payload.reason
        )
        return shipment_response(shipment, quantity=await shipments.item_count(shipment.id))
