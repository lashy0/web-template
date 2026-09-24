"""Production order controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import msgspec
from litestar import Controller, Request, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, QueryParameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.production.permissions import ProductionOrderPermission
from app.domain.production.schemas import (
    ProductionOrder,
    ProductionOrderCreate,
    ProductionOrderUpdate,
)
from app.domain.production.services import ProductionOrderService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

OrderId = Annotated[
    UUID,
    Parameter(title="Production order ID", description="The production order to act on."),
]


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
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_order_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.ProductionOrder,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="production_order",
            target_id=str(target.id),
            target_label=target.name,
            details=details,
            request=request,
        )

    @get(
        operation_id="ListProductionOrders",
        guards=[requires_permission(ProductionOrderPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_production_orders(
        self,
        production_orders_service: NamedDependency[ProductionOrderService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived: Annotated[
            bool | None,
            QueryParameter(description="Only archived (true) or only current (false) orders; all when omitted."),
        ] = None,
    ) -> OffsetPagination[ProductionOrder]:
        results, total = await production_orders_service.list_orders(*filters, archived=archived)

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
        request: Request[m.User, Any, Any],
        production_orders_service: NamedDependency[ProductionOrderService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: ProductionOrderCreate,
    ) -> ProductionOrder:
        db_obj = await production_orders_service.create(data.to_dict(), auto_commit=False)
        await self._log_order_action(
            request,
            audit_service,
            action="production_order.created",
            target=db_obj,
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
        request: Request[m.User, Any, Any],
        data: ProductionOrderUpdate,
        production_orders_service: NamedDependency[ProductionOrderService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        order_id: OrderId,
    ) -> ProductionOrder:
        db_obj = await production_orders_service.update_order(order_id, data.to_dict())
        await self._log_order_action(
            request,
            audit_service,
            action="production_order.updated",
            target=db_obj,
            details={
                "fields": [field for field in ("name", "description") if getattr(data, field) is not msgspec.UNSET]
            },
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
        request: Request[m.User, Any, Any],
        production_orders_service: NamedDependency[ProductionOrderService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        order_id: OrderId,
    ) -> ProductionOrder:
        return await self._set_archived(
            request,
            production_orders_service,
            audit_service,
            order_id,
            archived=True,
        )

    @post(
        operation_id="RestoreProductionOrder",
        path="/{order_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(ProductionOrderPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_production_order(
        self,
        request: Request[m.User, Any, Any],
        production_orders_service: NamedDependency[ProductionOrderService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        order_id: OrderId,
    ) -> ProductionOrder:
        return await self._set_archived(
            request,
            production_orders_service,
            audit_service,
            order_id,
            archived=False,
        )

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        production_orders_service: ProductionOrderService,
        audit_service: AuditLogService,
        order_id: UUID,
        *,
        archived: bool,
    ) -> ProductionOrder:
        was_archived = (await production_orders_service.get(order_id)).archived_at is not None
        db_obj = await production_orders_service.set_archived(order_id, archived=archived)

        if was_archived != archived:
            await self._log_order_action(
                request,
                audit_service,
                action="production_order.archived" if archived else "production_order.restored",
                target=db_obj,
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
        request: Request[m.User, Any, Any],
        production_orders_service: NamedDependency[ProductionOrderService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        order_id: OrderId,
    ) -> None:
        target = await production_orders_service.delete_order(order_id)
        await self._log_order_action(
            request,
            audit_service,
            action="production_order.deleted",
            target=target,
        )
