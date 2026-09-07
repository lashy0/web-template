from typing import cast

from fastapi import Request

from ..models import KgDevEuiPrefix, KgUnit
from ..schemas import KgDevEuiPrefixResponse, KgResponse
from ..services import KgDevEuiPrefixManagementService, KgManagementService


def _response(kg: KgUnit) -> KgResponse:
    return KgResponse(
        dev_eui=kg.dev_eui,
        short_id=kg.short_id,
        batch_id=kg.batch_id,
        status=kg.status,
        created_at=kg.created_at,
        updated_at=kg.updated_at,
    )


def _prefix_response(item: KgDevEuiPrefix) -> KgDevEuiPrefixResponse:
    return KgDevEuiPrefixResponse(
        prefix=item.prefix,
        short_code=item.short_code,
        name=item.name,
        created_at=item.created_at,
        archived_at=item.archived_at,
    )


def _service(request: Request) -> KgManagementService:
    return cast(KgManagementService, request.app.state.kg_management)


def _prefix_service(request: Request) -> KgDevEuiPrefixManagementService:
    return cast(KgDevEuiPrefixManagementService, request.app.state.kg_dev_eui_prefix_management)
