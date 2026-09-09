from typing import cast

from fastapi import Request

from ..models import ProductionOrder
from ..schemas import ProductionOrderResponse
from ..services import ProductionOrderManagementService


def _service(request: Request) -> ProductionOrderManagementService:
    return cast(ProductionOrderManagementService, request.app.state.production_order_management)


def _response(
    item: ProductionOrder, *, batches_count: int, total_planned_qty: int
) -> ProductionOrderResponse:
    return ProductionOrderResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        created_at=item.created_at,
        updated_at=item.updated_at,
        archived_at=item.archived_at,
        batches_count=batches_count,
        total_planned_qty=total_planned_qty,
    )
