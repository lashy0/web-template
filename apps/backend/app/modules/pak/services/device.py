from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService

from ..enums import PakDeviceKind
from ..exceptions import PakAlreadyExistsError
from ..models import PakDevice
from ..repository import PakRepository
from .audit import _audit_actor, _audit_entity
from .lifecycle import _ensure_not_archived
from .queries import _required_pak


class PakDeviceService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(self, pak_id: UUID) -> PakDevice | None:
        async with self._session_factory() as session:
            return await PakRepository(session).get_by_id(pak_id)

    async def list(
        self,
        *,
        q: str | None,
        kind: PakDeviceKind | None,
        active: bool | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[PakDevice], int]:
        async with self._session_factory() as session:
            return await PakRepository(session).search(
                q=q,
                kind=kind,
                active=active,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
        code: str | None,
        kind: PakDeviceKind | None,
    ) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await _required_pak(repository, pak_id)

            _ensure_not_archived(pak)

            old_values = {
                "code": pak.code,
                "kind": pak.kind.value,
            }

            if code is not None and code != pak.code:
                existing = await repository.get_by_code(code)

                if existing is not None and existing.id != pak.id:
                    raise PakAlreadyExistsError

            try:
                pak = await repository.update_details(pak, code=code, kind=kind)

            except IntegrityError as exc:
                raise PakAlreadyExistsError from exc

            new_values = {
                "code": pak.code,
                "kind": pak.kind.value,
            }
            new_data = {
                key: value for key, value in new_values.items() if value != old_values[key]
            }

            if new_data:
                await AuditService.from_session(session).record(
                    actor=_audit_actor(actor),
                    action="pak.updated",
                    entity=_audit_entity(pak),
                    old_data={key: old_values[key] for key in new_data},
                    new_data=new_data,
                )

            return pak

    async def set_active(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
        active: bool,
    ) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await _required_pak(repository, pak_id)

            _ensure_not_archived(pak)

            old_active = pak.is_active

            if old_active == active:
                return pak

            pak = await repository.update_active(pak, active=active)

            await AuditService.from_session(session).record(
                actor=_audit_actor(actor),
                action="pak.active_changed",
                entity=_audit_entity(pak),
                old_data={"active": old_active},
                new_data={"active": active},
            )

            return pak

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
        archived: bool,
    ) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await _required_pak(repository, pak_id)

            if not archived:
                if pak.archived_at is None:
                    return pak

                pak = await repository.update_archived(pak, archived_at=None)
                action = "pak.restored"

            else:
                if pak.archived_at is not None:
                    return pak

                if pak.is_active:
                    pak = await repository.update_active(pak, active=False)

                archived_at = datetime.now(UTC)
                pak = await repository.update_archived(pak, archived_at=archived_at)
                action = "pak.archived"

            await AuditService.from_session(session).record(
                actor=_audit_actor(actor),
                action=action,
                entity=_audit_entity(pak),
            )

            return pak
