from collections.abc import Mapping

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.batch.repository import BatchRepository
from app.modules.kg.exceptions import (
    KgCannotBeDeletedError,
    KgDevEuiPrefixConflictError,
    KgDevEuiPrefixInUseError,
    KgDevEuiPrefixNotFoundError,
    KgNotFoundError,
)
from app.modules.kg.models import KgDevEuiPrefix, KgStatus, KgUnit
from app.modules.kg.repository import KgDevEuiPrefixRepository, KgRepository
from app.modules.verification.repository import VerificationSessionRepository


class KgManagementService:
    """Coordinator KG lifecycle state, persistence, and audit."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(self, dev_eui: str) -> KgUnit | None:
        async with self._session_factory() as session:
            return await KgRepository(session).get_by_dev_eui(dev_eui)

    async def list(self, **filters: object) -> tuple[list[KgUnit], int]:
        async with self._session_factory() as session:
            return await KgRepository(session).search(**filters)  # type: ignore[arg-type]

    async def set_status(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
        status: KgStatus,
    ) -> KgUnit:
        async with self._session_factory() as session, session.begin():
            repository = KgRepository(session)

            kg = await self._required_kg(repository, dev_eui)

            if kg.status == status:
                return kg

            old_status = kg.status

            kg = await repository.update_status(kg, status=status)

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="kg.status_changed",
                entity=self._audit_entity(kg),
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
        async with self._session_factory() as session, session.begin():
            repository = KgRepository(session)

            kg = await self._required_kg(repository, dev_eui)

            self._ensure_can_delete(kg)

            if await VerificationSessionRepository(
                session
            ).exists_by_kg_dev_eui(kg.dev_eui):
                raise KgCannotBeDeletedError

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="kg.deleted",
                entity=self._audit_entity(kg),
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
        kg = await repository.get_by_dev_eui(dev_eui)

        if kg is None:
            raise KgNotFoundError

        return kg

    @staticmethod
    def _ensure_can_delete(kg: KgUnit) -> None:
        if kg.status != KgStatus.REGISTERED:
            raise KgCannotBeDeletedError

    @staticmethod
    def _audit_actor(actor: CurrentPrincipal) -> AuditActor:
        return AuditActor.user(
            actor.user_id,
            name=actor.name,
            login=actor.login,
        )

    @staticmethod
    def _audit_entity(kg: KgUnit) -> AuditEntity:
        return AuditEntity(
            type="kg",
            id=kg.dev_eui,
            display_name=kg.dev_eui,
            identifier=kg.dev_eui,
        )


class KgDevEuiPrefixManagementService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list(
        self,
    ) -> list[KgDevEuiPrefix]:
        async with self._session_factory() as session:
            return await KgDevEuiPrefixRepository(session).list()

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        short_code: str,
        name: str | None,
    ) -> KgDevEuiPrefix:
        async with self._session_factory() as session, session.begin():
            repository = KgDevEuiPrefixRepository(session)

            if await repository.get(prefix) is not None:
                raise KgDevEuiPrefixConflictError

            if (
                await repository.get_by_short_code(
                    short_code
                )
                is not None
            ):
                raise KgDevEuiPrefixConflictError

            try:
                item = await repository.create(
                    prefix=prefix,
                    short_code=short_code,
                    name=name,
                )

            except IntegrityError as exc:
                raise KgDevEuiPrefixConflictError from exc

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="kg_prefix.created",
                entity=self._audit_entity(item),
                new_data={
                    "prefix": item.prefix,
                    "short_code": item.short_code,
                    "name": item.name,
                },
            )

            return item

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        updates: Mapping[str, object],
    ) -> KgDevEuiPrefix:
        async with self._session_factory() as session, session.begin():
            repository = KgDevEuiPrefixRepository(session)

            item = await self._required(repository, prefix)

            if not updates:
                return item

            old_values = {
                field: getattr(item, field)
                for field in updates
            }

            item = await repository.update_details(
                item,
                updates=updates,
            )

            new_values = {
                field: getattr(item, field)
                for field in updates
            }

            changed = {
                field: value
                for field, value in new_values.items()
                if value != old_values[field]
            }

            if changed:
                await AuditService.from_session(session).record(
                    actor=self._audit_actor(actor),
                    action="kg_prefix.updated",
                    entity=self._audit_entity(item),
                    old_data={
                        field: old_values[field]
                        for field in changed
                    },
                    new_data=changed,
                )

            return item

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            repository = KgDevEuiPrefixRepository(session)

            item = await self._required(repository, prefix)

            in_use = await BatchRepository(
                session
            ).exists_by_dev_eui_prefix(
                item.prefix
            )

            if in_use:
                raise KgDevEuiPrefixInUseError

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="kg_prefix.deleted",
                entity=self._audit_entity(item),
                old_data={
                    "prefix": item.prefix,
                    "short_code": item.short_code,
                    "name": item.name,
                },
            )

            await repository.delete(item)

    @staticmethod
    async def _required(
        repository: KgDevEuiPrefixRepository,
        prefix: str,
    ) -> KgDevEuiPrefix:
        item = await repository.get(prefix)

        if item is None:
            raise KgDevEuiPrefixNotFoundError

        return item

    @staticmethod
    def _audit_actor(actor: CurrentPrincipal) -> AuditActor:
        return AuditActor.user(
            actor.user_id,
            name=actor.name,
            login=actor.login,
        )

    @staticmethod
    def _audit_entity(item: KgDevEuiPrefix) -> AuditEntity:
        return AuditEntity(
            type="kg_dev_eui_prefix",
            id=item.prefix,
            display_name=item.name or item.prefix,
            identifier=item.prefix,
        )
