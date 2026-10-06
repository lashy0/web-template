"""KG unit controllers."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from advanced_alchemy.filters import (
    BeforeAfter,
    CollectionFilter,
    ExistsFilter,
    FilterGroup,
    FilterTypes,
    StatementFilter,
)
from litestar import Controller, get
from litestar.datastructures import CacheControlHeader
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, QueryParameter, SkipValidation
from sqlalchemy import or_

from app.db import models as m
from app.db.enums import BatchShipmentStatus, KgOtkStatus, KgState, PakDeviceKind, VerificationSessionStatus
from app.domain.production.permissions import KgUnitPermission
from app.domain.production.schemas import KgOtkFilter, KgTimelineEvent, KgUnit, KgUnitCredentials
from app.domain.production.services import KgUnitService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.lorawan import normalize_dev_eui
from app.lib.openapi import error_responses

if TYPE_CHECKING:
    from advanced_alchemy.service.pagination import OffsetPagination

DevEui = Annotated[
    str,
    Parameter(title="DevEUI", description="The KG unit: 16 hexadecimal characters, any case."),
]


def _moment(name: str, description: str) -> QueryParameter:
    return QueryParameter(name=name, description=description)


def provide_kg_unit_date_filters(
    last_verification_after: Annotated[
        datetime | None,
        _moment("lastVerificationAfter", "Only units whose last OTK completed after this moment."),
    ] = None,
    last_verification_before: Annotated[
        datetime | None,
        _moment("lastVerificationBefore", "Only units whose last OTK completed before this moment."),
    ] = None,
    packed_after: Annotated[
        datetime | None,
        _moment("packedAfter", "Only units packed after this moment."),
    ] = None,
    packed_before: Annotated[
        datetime | None,
        _moment("packedBefore", "Only units packed before this moment."),
    ] = None,
    shipped_after: Annotated[
        datetime | None,
        _moment("shippedAfter", "Only units whose shipment completed after this moment."),
    ] = None,
    shipped_before: Annotated[
        datetime | None,
        _moment("shippedBefore", "Only units whose shipment completed before this moment."),
    ] = None,
) -> list[FilterTypes]:
    """Filter KG units by the dates their list shows; a unit without the date never matches."""
    filters: list[FilterTypes] = []
    if last_verification_after or last_verification_before:
        filters.append(BeforeAfter("last_verification_at", last_verification_before, last_verification_after))
    if packed_after or packed_before:
        filters.append(BeforeAfter("packed_at", packed_before, packed_after))
    if shipped_after or shipped_before:
        shipped = [
            m.BatchShipmentItem.dev_eui == m.KgUnit.dev_eui,
            m.BatchShipmentItem.voided_at.is_(None),
            m.BatchShipment.id == m.BatchShipmentItem.shipment_id,
            m.BatchShipment.status == BatchShipmentStatus.COMPLETED,
        ]
        if shipped_after:
            shipped.append(m.BatchShipment.completed_at > shipped_after)
        if shipped_before:
            shipped.append(m.BatchShipment.completed_at < shipped_before)
        filters.append(ExistsFilter(shipped))
    return filters


def provide_kg_unit_otk_filter(
    otk_in: Annotated[
        list[KgOtkFilter] | None,
        QueryParameter(
            name="otkIn",
            description="Only units with one of these last OTK results or, for `running`, on an OTK-line PAK now.",
        ),
    ] = None,
) -> list[FilterTypes]:
    """Filter KG units by OTK; the values add up, so `running` adds the units on a PAK to the results."""
    if not otk_in:
        return []

    matches: list[StatementFilter] = []
    statuses = [KgOtkStatus(value) for value in otk_in if value is not KgOtkFilter.RUNNING]
    if statuses:
        matches.append(CollectionFilter("otk_status", statuses))
    if KgOtkFilter.RUNNING in otk_in:
        matches.append(
            ExistsFilter(
                [
                    m.VerificationSession.dev_eui == m.KgUnit.dev_eui,
                    m.VerificationSession.status == VerificationSessionStatus.RUNNING,
                    m.VerificationSession.pak_kind == PakDeviceKind.OTK_LINE,
                ]
            )
        )
    return [FilterGroup(logical_operator=or_, filters=matches)]


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
    dependencies["date_filters"] = Provide(provide_kg_unit_date_filters, sync_to_thread=False)
    dependencies["otk_filter"] = Provide(provide_kg_unit_otk_filter, sync_to_thread=False)

    @get(
        operation_id="ListKgUnits",
        guards=[requires_permission(KgUnitPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_kg_units(
        self,
        kg_units_service: NamedDependency[KgUnitService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        date_filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        otk_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[KgUnit]:
        results, total = await kg_units_service.get_many_and_count(*filters, *date_filters, *otk_filter)

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

    @get(
        operation_id="GetKgUnitTimeline",
        path="/{dev_eui:str}/timeline",
        guards=[requires_permission(KgUnitPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_kg_unit_timeline(
        self,
        kg_units_service: NamedDependency[KgUnitService],
        dev_eui: DevEui,
    ) -> list[KgTimelineEvent]:
        """What happened to the unit, oldest first; see ``docs/domain/batches.md``."""
        return await kg_units_service.get_timeline(normalize_dev_eui(dev_eui))

    @get(
        operation_id="GetKgUnitCredentials",
        path="/{dev_eui:str}/credentials",
        guards=[requires_permission(KgUnitPermission.READ_CREDENTIALS)],
        responses=error_responses(401, 403, 404),
        # The keys must not stay in a browser or proxy cache.
        cache_control=CacheControlHeader(no_store=True),
    )
    async def get_kg_unit_credentials(
        self,
        kg_units_service: NamedDependency[KgUnitService],
        dev_eui: DevEui,
    ) -> KgUnitCredentials:
        """The LoRaWAN identifiers and keys of the unit; see ``docs/domain/batches.md``."""
        return await kg_units_service.get_credentials(normalize_dev_eui(dev_eui))
