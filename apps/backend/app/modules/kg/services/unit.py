from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.verification.repositories import VerificationSessionRepository

from ..exceptions import KgCannotBeDeletedError, KgNotFoundError
from ..models import KgState, KgUnit
from ..repositories import KgRepository
from ..repositories.unit import KgListItem
from ..schemas.state import KgCurrentState
from ..schemas.unit import KgBatchListItem
from . import audit, lifecycle


class KgService:
    """KG operations joining a caller-owned transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = KgRepository(session)

    async def lock_for_update(self, dev_euis: Sequence[str]) -> list[KgUnit]:
        return await self._repository.get_many_by_dev_euis(dev_euis, for_update=True)

    async def begin_verification(self, dev_eui: str) -> KgUnit:
        kg = await self._required_kg(self._repository, dev_eui)

        lifecycle.ensure_verification_ready(kg)

        return kg

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
    ) -> tuple[list[KgBatchListItem], int]:
        return await self._repository.list_batch_items(
            batch_id,
            page=page,
            page_size=page_size,
            q=q,
            current_state=current_state,
        )

    async def set_state(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
        state: KgState,
    ) -> KgUnit:
        kg = await self._required_kg(self._repository, dev_eui)

        if kg.state is state:
            return kg

        old_state = kg.state
        kg = await self._repository.update_state(kg, state=state)

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            action="kg.state_changed",
            entity=audit.unit_entity(kg),
            old_data={"state": old_state.value},
            new_data={"state": kg.state.value},
        )

        return kg

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
    ) -> None:
        kg = await self._required_kg(self._repository, dev_eui)
        lifecycle.ensure_can_delete(kg)

        if await VerificationSessionRepository(self._session).exists_by_kg_dev_eui(kg.dev_eui):
            raise KgCannotBeDeletedError

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            action="kg.deleted",
            entity=audit.unit_entity(kg),
            old_data={
                "dev_eui": kg.dev_eui,
                "batch_id": str(kg.batch_id),
                "state": kg.state.value,
            },
        )

        await self._repository.delete(kg)

    @staticmethod
    async def _required_kg(repository: KgRepository, dev_eui: str) -> KgUnit:
        kg = await repository.get_by_dev_eui(dev_eui, for_update=True)

        if kg is None:
            raise KgNotFoundError

        return kg

    async def allocate_for_batch(
        self,
        *,
        batch_id: UUID,
        dev_euis: Sequence[str],
        short_code: str,
    ) -> list[KgUnit]:
        return await self._repository.create_many(
            batch_id=batch_id, dev_euis=dev_euis, short_code=short_code
        )

    async def has_production_activity(self, batch_id: UUID) -> bool:
        return await self._repository.has_non_registered_by_batch(batch_id)

    async def delete_registered_for_batch(self, batch_id: UUID) -> None:
        units = await self._repository.list_by_batch(batch_id, for_update=True)

        for kg in units:
            lifecycle.ensure_can_delete(kg)

        await self._repository.delete_by_batch(batch_id)
