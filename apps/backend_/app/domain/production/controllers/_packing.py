"""Packing workstation controllers."""

from __future__ import annotations

from typing import Annotated, Any

from litestar import Controller, Request, get, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK

from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.production.permissions import PackingPermission
from app.domain.production.schemas import PackingBlocker, PackingUnit, PackingUnitBatch
from app.domain.production.services import PackingService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.lorawan import normalize_dev_eui
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

UnitCode = Annotated[
    str,
    Parameter(title="DevEUI or short ID", description="As scanned from the unit, in any case."),
]
DevEui = Annotated[
    str,
    Parameter(title="DevEUI", description="The KG unit: 16 hexadecimal characters, any case."),
]


def _to_packing_unit(kg: m.KgUnit, blocker: PackingBlocker | None) -> PackingUnit:
    return PackingUnit(
        dev_eui=kg.dev_eui,
        short_id=kg.short_id,
        state=kg.state,
        otk_status=kg.otk_status,
        last_verification_at=kg.last_verification_at,
        packed_at=kg.packed_at,
        batch=PackingUnitBatch(
            id=kg.batch.id,
            name=kg.batch.name,
            join_eui=kg.batch.join_eui,
        ),
        can_pack=blocker is None,
        blocked_by=blocker,
    )


class PackingController(Controller):
    """Packing of KG units that passed OTK; the label is printed by the workstation."""

    tags = ["Packing"]  # noqa: RUF012
    path = "/packing/units"
    dependencies = create_service_dependencies(PackingService, key="packing_service")
    dependencies["audit_service"] = Provide(provide_audit_log_service)

    @get(
        operation_id="FindPackingUnit",
        path="/{code:str}",
        guards=[requires_permission(PackingPermission.PACK)],
        responses=error_responses(401, 403, 404),
    )
    async def find_unit(
        self,
        packing_service: NamedDependency[PackingService],
        code: UnitCode,
    ) -> PackingUnit:
        kg, blocker = await packing_service.find_unit(code)

        return _to_packing_unit(kg, blocker)

    @post(
        operation_id="PackKgUnit",
        path="/{dev_eui:str}/pack",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PackingPermission.PACK)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def pack_unit(
        self,
        request: Request[m.User, Any, Any],
        packing_service: NamedDependency[PackingService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        dev_eui: DevEui,
    ) -> PackingUnit:
        kg = await packing_service.pack(normalize_dev_eui(dev_eui), packed_by_id=request.user.id)
        await audit_service.log_action(
            action="kg.packed",
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="kg_unit",
            target_id=kg.dev_eui,
            target_label=kg.short_id,
            details={"batch_id": str(kg.batch_id)},
            request=request,
        )

        return _to_packing_unit(kg, PackingBlocker.ALREADY_PACKED)
