from dataclasses import dataclass

from app.components.keygen.dev_eui import derive_dev_eui_range
from app.components.keygen.exceptions import DevEuiRangeOverflowError

from ..exceptions import (
    KgDevEuiPrefixNotFoundError,
    KgDevEuiRangeOverflowError,
)
from ..model import KgDevEuiPrefix
from ..repository import KgRepository
from ..rules import ensure_prefix_available_for_allocation


@dataclass(frozen=True, slots=True)
class BatchAllocation:
    prefix: KgDevEuiPrefix
    dev_euis: list[str]


class AllocateForBatch:
    """Make a locked, contiguous allocation decision inside the caller's UoW."""

    def __init__(self, repository: KgRepository) -> None:
        self._repository = repository

    async def execute(self, *, prefix: str, quantity: int) -> BatchAllocation:
        await self._repository.lock_allocation(prefix)
        item = await self._repository.get_prefix(prefix)
        if item is None:
            raise KgDevEuiPrefixNotFoundError
        ensure_prefix_available_for_allocation(item)
        try:
            first, last = derive_dev_eui_range(
                item.prefix,
                quantity,
                maximum_dev_eui=await self._repository.get_max_dev_eui_for_prefix(item.prefix),
            )
        except DevEuiRangeOverflowError:
            raise KgDevEuiRangeOverflowError from None
        start, end = int(first[-6:], 16), int(last[-6:], 16)
        return BatchAllocation(
            item, [f"{item.prefix}{value:06x}" for value in range(start, end + 1)]
        )
