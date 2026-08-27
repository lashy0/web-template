from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.auth_deps import CurrentPrincipalDep, require_permission
from app.api.deps import DatabaseDep
from app.modules.audit.permissions import AuditPermission
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import AuditEventResponse, AuditListResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListResponse)
async def list_audit_events(
    _: Annotated[CurrentPrincipalDep, Depends(require_permission(AuditPermission.READ))],
    database: DatabaseDep,
    entity_type: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["created_at", "actor_display_name"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> AuditListResponse:
    async with database.session_factory() as session:
        events, total = await AuditRepository(session).search(
            created_from=created_from,
            created_to=created_to,
            entity_type=entity_type,
            order=order,
            page=page,
            page_size=page_size,
            sort=sort,
        )

    return AuditListResponse(
        items=[
            AuditEventResponse(
                id=event.id,
                created_at=event.created_at,
                actor_type=event.actor_type,
                actor_id=event.actor_id,
                actor_display_name=event.actor_display_name,
                actor_identifier=event.actor_identifier,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                entity_display_name=event.entity_display_name,
                entity_identifier=event.entity_identifier,
                old_data=event.old_data,
                new_data=event.new_data,
            )
            for event in events
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
