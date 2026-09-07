from __future__ import annotations

import builtins
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal

from ..models import KgDevEuiPrefix, KgStatus, KgUnit
from .prefix import KgPrefixService as KgPrefixService
from .transactions import transaction
from .unit import KgService as KgService


class KgManagementService:
    """API gateway owning sessions and transactions; delegates domain operations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(self, dev_eui: str) -> KgUnit | None:
        async with self._session_factory() as session:
            return await KgService(session).get(dev_eui)

    async def list(
        self,
        *,
        q: str | None,
        batch_id: UUID | None,
        status: KgStatus | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[builtins.list[KgUnit], int]:
        async with self._session_factory() as session:
            return await KgService(session).list(
                q=q,
                batch_id=batch_id,
                status=status,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def set_status(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
        status: KgStatus,
    ) -> KgUnit:
        async with transaction(self._session_factory) as session:
            return await KgService(
                session,
            ).set_status(actor=actor, dev_eui=dev_eui, status=status)

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
    ) -> None:
        async with transaction(self._session_factory) as session:
            return await KgService(session).delete(actor=actor, dev_eui=dev_eui)


class KgDevEuiPrefixManagementService:
    """API gateway owning sessions and transactions; delegates domain operations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list(
        self,
    ) -> builtins.list[KgDevEuiPrefix]:
        async with self._session_factory() as session:
            return await KgPrefixService(session).list()

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        short_code: str,
        name: str | None,
    ) -> KgDevEuiPrefix:
        async with transaction(self._session_factory) as session:
            return await KgPrefixService(session).create(
                actor=actor, prefix=prefix, short_code=short_code, name=name
            )

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        updates: Mapping[str, object],
    ) -> KgDevEuiPrefix:
        async with transaction(self._session_factory) as session:
            return await KgPrefixService(session).update(
                actor=actor, prefix=prefix, updates=updates
            )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
    ) -> None:
        async with transaction(self._session_factory) as session:
            return await KgPrefixService(session).delete(actor=actor, prefix=prefix)
