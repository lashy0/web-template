from .exceptions import DefectGroupArchivedError, DefectGroupHasUnarchivedTypesError
from .model import DefectGroup, DefectType


def ensure_group_active(group: DefectGroup) -> None:
    if group.archived_at is not None:
        raise DefectGroupArchivedError


def ensure_group_can_be_archived(*, group: DefectGroup, has_unarchived_types: bool) -> None:
    if group.archived_at is None and has_unarchived_types:
        raise DefectGroupHasUnarchivedTypesError


def group_snapshot(group: DefectGroup) -> dict[str, object]:
    return {
        "code": group.code,
        "name": group.name,
        "description": group.description,
        "archived_at": group.archived_at.isoformat() if group.archived_at is not None else None,
    }


def type_snapshot(item: DefectType) -> dict[str, object]:
    return {
        "group_id": str(item.group_id),
        "code": item.code,
        "name": item.name,
        "description": item.description,
        "possible_cause": item.possible_cause,
        "engineer_action": item.engineer_action,
        "archived_at": item.archived_at.isoformat() if item.archived_at is not None else None,
    }
