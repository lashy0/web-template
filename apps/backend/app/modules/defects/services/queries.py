from uuid import UUID

from ..exceptions import DefectGroupNotFoundError, DefectTypeNotFoundError
from ..models import DefectGroup, DefectType
from ..repositories import DefectGroupRepository, DefectTypeRepository


async def _required_group(
    repository: DefectGroupRepository,
    group_id: UUID,
) -> DefectGroup:
    group = await repository.get_by_id(group_id, for_update=True)

    if group is None:
        raise DefectGroupNotFoundError

    return group


async def _required_type(
    repository: DefectTypeRepository,
    defect_type_id: UUID,
) -> DefectType:
    defect_type = await repository.get_by_id(defect_type_id, for_update=True)

    if defect_type is None:
        raise DefectTypeNotFoundError

    return defect_type
