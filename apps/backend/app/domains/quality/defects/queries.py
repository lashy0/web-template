from uuid import UUID

from .exceptions import DefectGroupNotFoundError, DefectTypeNotFoundError
from .model import DefectGroup, DefectType
from .repository import DefectGroupRepository, DefectTypeRepository


class DefectQueries:
    def __init__(self, groups: DefectGroupRepository, types: DefectTypeRepository) -> None:
        self._groups = groups
        self._types = types

    async def get_group(self, group_id: UUID) -> DefectGroup | None:
        return await self._groups.get(group_id)

    async def get_group_by_code(self, code: str, *, for_update: bool = False) -> DefectGroup | None:
        return await self._groups.get_by_code(code, for_update=for_update)

    async def list_groups(self, **kwargs: object) -> tuple[list[tuple[DefectGroup, int, int]], int]:
        return await self._groups.search(**kwargs)  # type: ignore[arg-type]

    async def get_type(self, item_id: UUID) -> DefectType | None:
        return await self._types.get(item_id)

    async def get_type_by_code(self, code: str) -> DefectType | None:
        return await self._types.get_by_code(code)

    async def list_types(self, **kwargs: object) -> tuple[list[DefectType], int]:
        return await self._types.search(**kwargs)  # type: ignore[arg-type]


async def required_group(repository: DefectGroupRepository, group_id: UUID) -> DefectGroup:
    item = await repository.get(group_id, for_update=True)
    if item is None:
        raise DefectGroupNotFoundError
    return item


async def required_type(repository: DefectTypeRepository, item_id: UUID) -> DefectType:
    item = await repository.get(item_id, for_update=True)
    if item is None:
        raise DefectTypeNotFoundError
    return item
