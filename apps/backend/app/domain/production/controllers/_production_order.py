"""Production order controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.service import schema_dump
from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.domain.audit.changes import ChangeRecorder
from app.domain.production.events import ProductionOrderChanged
from app.domain.production.permissions import ProductionOrderPermission
from app.domain.production.schemas import (
    ProductionOrder,
    ProductionOrderCreate,
    ProductionOrderUpdate,
)
from app.domain.production.services import ProductionOrderService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

OrderId = Annotated[
    UUID,
    Parameter(title="Production order ID", description="The production order to act on."),
]


_AUDIT_FIELDS = same_fields("name", "description")
"""Fields the ``updated`` audit entries compare."""


class ProductionOrderController(Controller):
    """Production orders."""

    tags = ["Production orders"]  # noqa: RUF012
    path = "/production-orders"
    dependencies = create_service_dependencies(
        ProductionOrderService,
        key="production_orders_service",
        filters={
            "id_filter": UUID,
            "search": "name,description",
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)

    @get(
        operation_id="ListProductionOrders",
        guards=[requires_permission(ProductionOrderPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_production_orders(
        self,
        production_orders_service: NamedDependency[ProductionOrderService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[ProductionOrder]:
        results, total = await production_orders_service.get_many_and_count(*filters, *archived_filter)

        return production_orders_service.to_schema(
            results,
            total,
            filters,
            schema_type=ProductionOrder,
        )

    @get(
        operation_id="GetProductionOrder",
        path="/{order_id:uuid}",
        guards=[requires_permission(ProductionOrderPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_production_order(
        self,
        production_orders_service: NamedDependency[ProductionOrderService],
        order_id: OrderId,
    ) -> ProductionOrder:
        db_obj = await production_orders_service.get(order_id)

        return production_orders_service.to_schema(db_obj, schema_type=ProductionOrder)

    @post(
        operation_id="CreateProductionOrder",
        path="",
        guards=[requires_permission(ProductionOrderPermission.CREATE)],
        responses=error_responses(401, 403),
    )
    async def create_production_order(
        self,
        production_orders_service: NamedDependency[ProductionOrderService],
        changes: NamedDependency[ChangeRecorder],
        data: ProductionOrderCreate,
    ) -> ProductionOrder:
        db_obj = await production_orders_service.create_order(schema_dump(data))
        await changes.record(
            "production_order.created",
            db_obj,
            event=ProductionOrderChanged(order_id=db_obj.id),
        )

        return production_orders_service.to_schema(db_obj, schema_type=ProductionOrder)

    @patch(
        operation_id="UpdateProductionOrder",
        path="/{order_id:uuid}",
        guards=[requires_permission(ProductionOrderPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_production_order(
        self,
        data: ProductionOrderUpdate,
        production_orders_service: NamedDependency[ProductionOrderService],
        changes: NamedDependency[ChangeRecorder],
        order_id: OrderId,
    ) -> ProductionOrder:
        before = snapshot(await production_orders_service.get(order_id), _AUDIT_FIELDS)
        db_obj = await production_orders_service.update_order(
            order_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )

        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await changes.record(
                "production_order.updated",
                db_obj,
                event=ProductionOrderChanged(order_id=db_obj.id),
                details=details,
            )

        return production_orders_service.to_schema(db_obj, schema_type=ProductionOrder)

    @post(
        operation_id="ArchiveProductionOrder",
        path="/{order_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(ProductionOrderPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def archive_production_order(
        self,
        production_orders_service: NamedDependency[ProductionOrderService],
        changes: NamedDependency[ChangeRecorder],
        order_id: OrderId,
    ) -> ProductionOrder:
        return await self._set_archived(production_orders_service, changes, order_id, archived=True)

    @post(
        operation_id="RestoreProductionOrder",
        path="/{order_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(ProductionOrderPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_production_order(
        self,
        production_orders_service: NamedDependency[ProductionOrderService],
        changes: NamedDependency[ChangeRecorder],
        order_id: OrderId,
    ) -> ProductionOrder:
        return await self._set_archived(production_orders_service, changes, order_id, archived=False)

    @staticmethod
    async def _set_archived(
        production_orders_service: ProductionOrderService,
        changes: ChangeRecorder,
        order_id: UUID,
        *,
        archived: bool,
    ) -> ProductionOrder:
        was_archived = (await production_orders_service.get(order_id)).archived_at is not None
        db_obj = await production_orders_service.set_archived(order_id, archived=archived)

        if was_archived != archived:
            await changes.record(
                "production_order.archived" if archived else "production_order.restored",
                db_obj,
                event=ProductionOrderChanged(order_id=db_obj.id),
            )

        return production_orders_service.to_schema(db_obj, schema_type=ProductionOrder)

    @delete(
        operation_id="DeleteProductionOrder",
        path="/{order_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(ProductionOrderPermission.DELETE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def delete_production_order(
        self,
        production_orders_service: NamedDependency[ProductionOrderService],
        changes: NamedDependency[ChangeRecorder],
        order_id: OrderId,
    ) -> None:
        target = await production_orders_service.delete_order(order_id)
        await changes.record(
            "production_order.deleted",
            target,
            event=ProductionOrderChanged(order_id=target.id),
        )
