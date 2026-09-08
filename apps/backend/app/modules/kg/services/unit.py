from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.verification.repositories import VerificationSessionRepository

from ..exceptions import KgCannotBeDeletedError, KgNotFoundError
from ..models import KgStatus, KgUnit
from ..repositories import KgRepository
from . import audit, lifecycle


class KgService:
    """KG operations joining a caller-owned transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = KgRepository(session)

    async def lock_for_update(self, dev_euis: Sequence[str]) -> list[KgUnit]:
        """Lock all affected KG in DevEUI order before changing several units."""
        return await self._repository.get_many_by_dev_euis(dev_euis, for_update=True)

    async def begin_verification(self, dev_eui: str) -> KgUnit:
        kg = await self._required_kg(self._repository, dev_eui)

        lifecycle.ensure_verification_ready(kg)

        await self._repository.update_status(kg, status=KgStatus.TESTING)

        return kg

    async def finish_verification(
        self,
        dev_eui: str,
        *,
        status: KgStatus,
    ) -> KgUnit:
        kg = await self._required_kg(self._repository, dev_eui)

        lifecycle.ensure_verification_completion_allowed(kg, status)

        await self._repository.update_status(kg, status=status)

        return kg

    async def release_incomplete_verification(self, dev_eui: str) -> None:
        kg = await self._repository.get_by_dev_eui(dev_eui, for_update=True)

        # Preserve explicit administrative corrections made while the run was active.
        if kg is not None and kg.status == KgStatus.TESTING:
            await self._repository.update_status(kg, status=KgStatus.READY_FOR_RETEST)

    async def get(self, dev_eui: str) -> KgUnit | None:
        session = self._session

        return await KgRepository(session).get_by_dev_eui(dev_eui)

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
    ) -> tuple[list[KgUnit], int]:
        session = self._session

        return await KgRepository(session).search(
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
        session = self._session
        repository = KgRepository(session)

        kg = await self._required_kg(repository, dev_eui)

        if kg.status == status:
            return kg

        old_status = kg.status

        kg = await repository.update_status(kg, status=status)

        await AuditService.from_session(session).record(
            actor=audit.actor_identity(actor),
            action="kg.status_changed",
            entity=audit.unit_entity(kg),
            old_data={
                "status": old_status.value,
            },
            new_data={
                "status": kg.status.value,
            },
        )

        return kg

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
    ) -> None:
        session = self._session
        repository = KgRepository(session)

        kg = await self._required_kg(repository, dev_eui)

        lifecycle.ensure_can_delete(kg)

        if await VerificationSessionRepository(session).exists_by_kg_dev_eui(kg.dev_eui):
            raise KgCannotBeDeletedError

        await AuditService.from_session(session).record(
            actor=audit.actor_identity(actor),
            action="kg.deleted",
            entity=audit.unit_entity(kg),
            old_data={
                "dev_eui": kg.dev_eui,
                "batch_id": str(kg.batch_id),
                "status": kg.status.value,
            },
        )

        await repository.delete(kg)

    @staticmethod
    async def _required_kg(
        repository: KgRepository,
        dev_eui: str,
    ) -> KgUnit:
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
            batch_id=batch_id,
            dev_euis=dev_euis,
            short_code=short_code,
        )

    async def require_packed(
        self,
        dev_eui: str,
        *,
        batch_id: UUID,
    ) -> KgUnit:
        kg = await self._repository.get_by_dev_eui(dev_eui, for_update=True)

        if kg is None:
            raise KgNotFoundError

        lifecycle.ensure_batch_state([kg], batch_id=batch_id, status=KgStatus.PACKED)

        return kg

    async def mark_shipped(
        self,
        dev_euis: Sequence[str],
        *,
        batch_id: UUID,
    ) -> None:
        await self._transition(
            dev_euis,
            batch_id,
            KgStatus.PACKED,
            KgStatus.SHIPPED,
        )

    async def return_to_packed(
        self,
        dev_euis: Sequence[str],
        *,
        batch_id: UUID,
    ) -> None:
        await self._transition(
            dev_euis,
            batch_id,
            KgStatus.SHIPPED,
            KgStatus.PACKED,
        )

    async def _transition(
        self,
        dev_euis: Sequence[str],
        batch_id: UUID,
        previous: KgStatus,
        target: KgStatus,
    ) -> None:
        units = await self._repository.get_many_by_dev_euis(dev_euis, for_update=True)

        if len(units) != len(set(dev_euis)):
            raise KgNotFoundError

        lifecycle.ensure_batch_state(units, batch_id=batch_id, status=previous)

        await self._repository.update_status_many(units, status=target)

    async def has_production_activity(self, batch_id: UUID) -> bool:
        return await self._repository.has_non_registered_by_batch(batch_id)

    async def delete_registered_for_batch(self, batch_id: UUID) -> None:
        # Batch deletion has already checked history under the batch lock.
        units = await self._repository.list_by_batch(batch_id, for_update=True)

        for kg in units:
            lifecycle.ensure_can_delete(kg)

        await self._repository.delete_by_batch(batch_id)
