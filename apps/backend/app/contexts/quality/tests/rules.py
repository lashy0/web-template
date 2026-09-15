from app.contexts.quality.defects.model import DefectGroup
from app.contexts.quality.defects.rules import ensure_group_active


def ensure_observation_group_active(group: DefectGroup) -> None:
    ensure_group_active(group)
