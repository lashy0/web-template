from typing import cast

from fastapi import Request

from ..models import DefectGroup, DefectType
from ..schemas import (
    DefectGroupResponse,
    DefectGroupSummaryResponse,
    DefectTypeResponse,
)
from ..services import DefectManagementService


def _service(request: Request) -> DefectManagementService:
    return cast(
        DefectManagementService,
        request.app.state.defect_management,
    )


def _group_response(group: DefectGroup) -> DefectGroupResponse:
    return DefectGroupResponse(
        id=group.id,
        code=group.code,
        name=group.name,
        description=group.description,
        archived_at=group.archived_at,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def _type_response(defect_type: DefectType) -> DefectTypeResponse:
    return DefectTypeResponse(
        id=defect_type.id,
        group_id=defect_type.group_id,
        group=DefectGroupSummaryResponse(
            id=defect_type.group.id,
            code=defect_type.group.code,
            name=defect_type.group.name,
            archived_at=defect_type.group.archived_at,
        ),
        code=defect_type.code,
        name=defect_type.name,
        description=defect_type.description,
        possible_cause=defect_type.possible_cause,
        engineer_action=defect_type.engineer_action,
        archived_at=defect_type.archived_at,
        created_at=defect_type.created_at,
        updated_at=defect_type.updated_at,
    )
