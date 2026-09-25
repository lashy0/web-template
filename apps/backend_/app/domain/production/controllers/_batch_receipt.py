"""Receipt controllers nested under their batch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import msgspec
from advanced_alchemy.filters import FilterTypes, NotNullFilter, NullFilter
from litestar import Controller, Request, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, QueryParameter, SkipValidation
from litestar.status_codes import HTTP_200_OK

from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.production.permissions import BatchPermission
from app.domain.production.schemas import (
    BatchReceipt,
    BatchReceiptCreate,
    BatchReceiptUpdate,
    BatchReceiptVoid,
)
from app.domain.production.services import BatchReceiptService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.service.pagination import OffsetPagination

BatchId = Annotated[
    UUID,
    Parameter(title="Batch ID", description="The batch the receipts belong to."),
]
ReceiptId = Annotated[
    UUID,
    Parameter(title="Receipt ID", description="The receipt to act on."),
]


def provide_voided_filter(
    voided: Annotated[
        bool | None,
        QueryParameter(description="Only voided (true) or only valid (false) receipts; all when omitted."),
    ] = None,
) -> list[FilterTypes]:
    if voided is None:
        return []

    return [NotNullFilter("voided_at") if voided else NullFilter("voided_at")]


class BatchReceiptController(Controller):
    """Receipts of KG units produced by a batch."""

    tags = ["Batch Receipts"]  # noqa: RUF012
    path = "/batches/{batch_id:uuid}/receipts"
    dependencies = create_service_dependencies(
        BatchReceiptService,
        key="receipts_service",
        filters={
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
        },
    )
    dependencies["voided_filter"] = Provide(provide_voided_filter, sync_to_thread=False)
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @staticmethod
    async def _log_receipt_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.BatchReceipt,
        details: dict[str, Any],
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="batch_receipt",
            target_id=str(target.id),
            details={"batch_id": str(target.batch_id), **details},
            request=request,
        )

    @get(
        operation_id="ListBatchReceipts",
        path="",
        guards=[requires_permission(BatchPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def list_receipts(
        self,
        receipts_service: NamedDependency[BatchReceiptService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        voided_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
        batch_id: BatchId,
    ) -> OffsetPagination[BatchReceipt]:
        await receipts_service.ensure_batch_exists(batch_id)
        results, total = await receipts_service.get_many_and_count(
            m.BatchReceipt.batch_id == batch_id,
            *filters,
            *voided_filter,
        )

        return receipts_service.to_schema(results, total, filters, schema_type=BatchReceipt)

    @get(
        operation_id="GetBatchReceipt",
        path="/{receipt_id:uuid}",
        guards=[requires_permission(BatchPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_receipt(
        self,
        receipts_service: NamedDependency[BatchReceiptService],
        batch_id: BatchId,
        receipt_id: ReceiptId,
    ) -> BatchReceipt:
        db_obj = await receipts_service.get_receipt(batch_id, receipt_id)

        return receipts_service.to_schema(db_obj, schema_type=BatchReceipt)

    @post(
        operation_id="CreateBatchReceipt",
        path="",
        guards=[requires_permission(BatchPermission.CREATE_RECEIPT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def create_receipt(
        self,
        request: Request[m.User, Any, Any],
        receipts_service: NamedDependency[BatchReceiptService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: BatchReceiptCreate,
        batch_id: BatchId,
    ) -> BatchReceipt:
        db_obj = await receipts_service.create_receipt(batch_id, data, created_by_id=request.user.id)
        await self._log_receipt_action(
            request,
            audit_service,
            action="batch_receipt.created",
            target=db_obj,
            details={"quantity": db_obj.quantity},
        )

        return receipts_service.to_schema(db_obj, schema_type=BatchReceipt)

    @patch(
        operation_id="UpdateBatchReceipt",
        path="/{receipt_id:uuid}",
        guards=[requires_permission(BatchPermission.UPDATE_RECEIPT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_receipt(
        self,
        request: Request[m.User, Any, Any],
        receipts_service: NamedDependency[BatchReceiptService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: BatchReceiptUpdate,
        batch_id: BatchId,
        receipt_id: ReceiptId,
    ) -> BatchReceipt:
        db_obj = await receipts_service.update_receipt(batch_id, receipt_id, data.to_dict())
        await self._log_receipt_action(
            request,
            audit_service,
            action="batch_receipt.updated",
            target=db_obj,
            details={
                "fields": [field for field in ("quantity", "comment") if getattr(data, field) is not msgspec.UNSET],
                "quantity": db_obj.quantity,
            },
        )

        return receipts_service.to_schema(db_obj, schema_type=BatchReceipt)

    @post(
        operation_id="VoidBatchReceipt",
        path="/{receipt_id:uuid}/void",
        status_code=HTTP_200_OK,
        guards=[requires_permission(BatchPermission.VOID_RECEIPT)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def void_receipt(
        self,
        request: Request[m.User, Any, Any],
        receipts_service: NamedDependency[BatchReceiptService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        data: BatchReceiptVoid,
        batch_id: BatchId,
        receipt_id: ReceiptId,
    ) -> BatchReceipt:
        db_obj = await receipts_service.void_receipt(batch_id, receipt_id, data.reason)
        await self._log_receipt_action(
            request,
            audit_service,
            action="batch_receipt.voided",
            target=db_obj,
            details={"quantity": db_obj.quantity, "reason": data.reason},
        )

        return receipts_service.to_schema(db_obj, schema_type=BatchReceipt)
