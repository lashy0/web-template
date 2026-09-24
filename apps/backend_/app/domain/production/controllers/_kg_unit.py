"""KG unit controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.params import Parameter, SkipValidation

from app.db.enums import KgState
from app.domain.production.permissions import KgUnitPermission
from app.domain.production.schemas import KgUnit
from app.domain.production.services import KgUnitService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.lorawan import normalize_dev_eui
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

DevEui = Annotated[
    str,
    Parameter(title="DevEUI", description="The KG unit: 16 hexadecimal characters, any case."),
]


class KgUnitController(Controller):
    """KG units registered by batches; production processes change them, users only read."""

    tags = ["KG units"]  # noqa: RUF012
    path = "/kg/units"
    dependencies = create_service_dependencies(
        KgUnitService,
        key="kg_units_service",
        filters={
            "search": "dev_eui,short_id",
            "search_ignore_case": True,
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "sort_field": "dev_eui",
            "sort_order": "asc",
            "in_fields": [
                FieldNameType(name="batch_id", type_hint=UUID),
                FieldNameType(name="state", type_hint=KgState),
            ],
        },
    )

    @get(
        operation_id="ListKgUnits",
        guards=[requires_permission(KgUnitPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_kg_units(
        self,
        kg_units_service: NamedDependency[KgUnitService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[KgUnit]:
        results, total = await kg_units_service.get_many_and_count(*filters)

        return kg_units_service.to_schema(results, total, filters, schema_type=KgUnit)

    @get(
        operation_id="GetKgUnit",
        path="/{dev_eui:str}",
        guards=[requires_permission(KgUnitPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_kg_unit(
        self,
        kg_units_service: NamedDependency[KgUnitService],
        dev_eui: DevEui,
    ) -> KgUnit:
        db_obj = await kg_units_service.get(normalize_dev_eui(dev_eui))

        return kg_units_service.to_schema(db_obj, schema_type=KgUnit)
