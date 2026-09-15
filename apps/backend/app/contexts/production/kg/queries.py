from __future__ import annotations

import builtins
from uuid import UUID

from app.components.keygen.dev_eui import derive_dev_eui_range
from app.components.keygen.exceptions import DevEuiRangeOverflowError

from .exceptions import (
    KgDevEuiPrefixNotFoundError,
    KgDevEuiRangeOverflowError,
)
from .model import KgDevEuiPrefix, KgUnit, KgVersion
from .repository import KgListItem, KgRepository
from .rules import ensure_prefix_available_for_allocation
from .schemas.state import KgCurrentState
from .schemas.unit import KgBatchListItem


class KgQueries:
    def __init__(self, repository: KgRepository) -> None:
        self._repository = repository

    async def list_prefixes(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[KgDevEuiPrefix, int]], int]:
        return await self._repository.list_prefixes(
            q=q, archived=archived, page=page, page_size=page_size, sort=sort, order=order
        )

    async def list_versions(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[KgVersion, int]], int]:
        return await self._repository.list_versions(
            q=q,
            archived=archived,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def preview_allocation(self, prefix: str, quantity: int) -> tuple[str, str]:
        item = await self._repository.get_prefix(prefix)
        if item is None:
            raise KgDevEuiPrefixNotFoundError
        ensure_prefix_available_for_allocation(item)
        try:
            return derive_dev_eui_range(
                prefix,
                quantity,
                maximum_dev_eui=await self._repository.get_max_dev_eui_for_prefix(prefix),
            )
        except DevEuiRangeOverflowError:
            raise KgDevEuiRangeOverflowError from None

    async def get(self, dev_eui: str) -> KgUnit | None:
        return await self._repository.get_by_dev_eui(dev_eui)

    async def get_with_current_state(self, dev_eui: str) -> KgListItem | None:
        return await self._repository.get_with_current_state(dev_eui)

    async def list(
        self,
        *,
        q: str | None,
        batch_id: UUID | None,
        current_state: KgCurrentState | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[KgListItem], int]:
        return await self._repository.search(
            q=q,
            batch_id=batch_id,
            current_state=current_state,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def list_batch_items(
        self,
        batch_id: UUID,
        *,
        page: int,
        page_size: int,
        q: str | None,
        current_state: KgCurrentState | None,
    ) -> tuple[builtins.list[KgBatchListItem], int]:
        return await self._repository.list_batch_items(
            batch_id, page=page, page_size=page_size, q=q, current_state=current_state
        )
