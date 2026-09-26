from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import cast
from uuid import UUID

from advanced_alchemy.exceptions import IntegrityError, NotFoundError, RepositoryError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm.attributes import set_committed_value
from uuid_utils.compat import uuid7

from app.db import models as m
from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.exceptions import (
    PakDeviceArchivedError,
    PakDeviceCodeTakenError,
    PakDeviceInUseError,
)
from app.lib.exceptions import AuthenticationError, AuthorizationError
from app.lib.hydra import HydraClient
from app.lib.uow import UnitOfWork


class PakDeviceService(service.SQLAlchemyAsyncRepositoryService[m.PakDevice]):
    """Application service for PAK devices and their Hydra OAuth clients."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.PakDevice]):
        """PAK device SQLAlchemy repository."""

        model_type = m.PakDevice

        async def get_by_id(
            self,
            pak_id: UUID,
            *,
            for_update: bool = False,
        ) -> m.PakDevice | None:
            return await self.get_one_or_none(
                m.PakDevice.id == pak_id,
                with_for_update=for_update,
                # A locked read must replace what an earlier read left in the session.
                execution_options={"populate_existing": for_update},
            )

        async def get_by_code(self, code: str) -> m.PakDevice | None:
            return await self.get_one_or_none(m.PakDevice.code == code)

        async def get_by_oauth_client_id(self, oauth_client_id: str) -> m.PakDevice | None:
            return await self.get_one_or_none(
                m.PakDevice.oauth_client_id == oauth_client_id,
            )

    repository_type = Repo

    @property
    def _pak_repository(self) -> Repo:
        return cast("PakDeviceService.Repo", self.repository)

    async def get_by_id(
        self,
        pak_id: UUID,
        *,
        for_update: bool = False,
    ) -> m.PakDevice | None:
        return await self._pak_repository.get_by_id(
            pak_id,
            for_update=for_update,
        )

    async def get_by_code(self, code: str) -> m.PakDevice | None:
        return await self._pak_repository.get_by_code(code)

    async def get_by_oauth_client_id(self, oauth_client_id: str) -> m.PakDevice | None:
        return await self._pak_repository.get_by_oauth_client_id(oauth_client_id)

    async def create_pak(
        self,
        data: dict[str, object],
        *,
        hydra: HydraClient,
        cipher: PakAccessKeyCipher,
        uow: UnitOfWork,
    ) -> tuple[m.PakDevice, str]:
        await self._ensure_unique_code(data.get("code"))

        pak_id = uuid7()
        requested_client_id = f"pak-{pak_id}"
        credentials = await hydra.create_client(client_id=requested_client_id)
        # Not needed for safety: without a local row its tokens are rejected.
        uow.on_rollback(
            "pak.create.rollback",
            partial(hydra.delete_client, credentials.client.client_id),
        )

        if credentials.client.client_id != requested_client_id:
            raise RepositoryError("Hydra changed the PAK OAuth client ID during provisioning.")

        try:
            pak = await self.create(
                {
                    "id": pak_id,
                    **data,
                    "oauth_client_id": credentials.client.client_id,
                    "encrypted_access_key": cipher.encrypt(credentials.client_secret),
                },
                auto_commit=False,
            )
        except IntegrityError as error:
            raise PakDeviceCodeTakenError from error

        return pak, credentials.client_secret

    async def update_pak(self, pak_id: UUID, data: dict[str, object]) -> m.PakDevice:
        pak = await self._require(pak_id)

        if pak.archived_at is not None:
            raise PakDeviceArchivedError

        code = data.get("code")
        if code != pak.code:
            await self._ensure_unique_code(code)

        try:
            return await self.update(data, item_id=pak_id, auto_commit=False)
        except IntegrityError as error:
            raise PakDeviceCodeTakenError from error

    async def set_active(
        self,
        pak_id: UUID,
        *,
        is_active: bool,
        hydra: HydraClient,
        uow: UnitOfWork,
    ) -> m.PakDevice:
        pak = await self._require(pak_id, for_update=True)

        if pak.archived_at is not None:
            raise PakDeviceArchivedError

        if not is_active:
            uow.after_commit(
                "pak.deactivate",
                partial(hydra.revoke_client_tokens, pak.oauth_client_id),
            )

        pak.is_active = is_active
        await self.repository.session.flush()

        return pak

    async def set_archived(
        self,
        pak_id: UUID,
        *,
        archived: bool,
        hydra: HydraClient,
        uow: UnitOfWork,
    ) -> m.PakDevice:
        pak = await self._require(pak_id, for_update=True)

        if archived:
            pak.is_active = False

            if pak.archived_at is None:
                pak.archived_at = datetime.now(UTC)

            uow.after_commit(
                "pak.archive",
                partial(hydra.revoke_client_tokens, pak.oauth_client_id),
            )
        else:
            pak.archived_at = None

        await self.repository.session.flush()

        return pak

    async def get_access_key(
        self,
        pak_id: UUID,
        *,
        cipher: PakAccessKeyCipher,
    ) -> str:
        pak = await self._require(pak_id)

        return cipher.decrypt(pak.encrypted_access_key)

    async def rotate_access_key(
        self,
        pak_id: UUID,
        *,
        hydra: HydraClient,
        cipher: PakAccessKeyCipher,
        uow: UnitOfWork,
    ) -> tuple[m.PakDevice, str]:
        pak = await self._require(pak_id, for_update=True)

        if pak.archived_at is not None:
            raise PakDeviceArchivedError

        previous_secret = cipher.decrypt(pak.encrypted_access_key)
        credentials = await hydra.rotate_client_credentials(pak.oauth_client_id)
        uow.on_rollback(
            "pak.rotate_access_key.rollback",
            partial(hydra.set_client_secret, pak.oauth_client_id, previous_secret),
        )

        if credentials.client.client_id != pak.oauth_client_id:
            raise RepositoryError("Hydra changed the PAK OAuth client ID during credential rotation.")

        pak.encrypted_access_key = cipher.encrypt(credentials.client_secret)
        await self.repository.session.flush()
        uow.after_commit(
            "pak.rotate_access_key",
            partial(hydra.revoke_client_tokens, pak.oauth_client_id),
        )

        return pak, credentials.client_secret

    async def delete_pak(
        self,
        pak_id: UUID,
        *,
        hydra: HydraClient,
        uow: UnitOfWork,
    ) -> m.PakDevice:
        pak = await self._require(pak_id, for_update=True)

        if await self.repository.session.scalar(
            select(
                exists().where(m.VerificationSession.pak_id == pak.id)
            )
        ):
            raise PakDeviceInUseError

        await self.repository.session.delete(pak)
        await self.repository.session.flush()
        uow.after_commit(
            "pak.delete",
            partial(hydra.delete_client, pak.oauth_client_id),
        )

        return pak

    async def authorize_machine_access_token(
        self,
        access_token: str,
        *,
        hydra: HydraClient,
    ) -> m.PakDevice:
        introspection = await hydra.introspect_access_token(access_token)

        if not introspection.active or introspection.client_id is None:
            raise AuthenticationError(detail="PAK access token is invalid.")

        pak = await self.get_by_oauth_client_id(introspection.client_id)

        if pak is None:
            raise AuthenticationError(detail="PAK access token is invalid.")

        if not pak.is_active or pak.archived_at is not None:
            raise AuthorizationError(detail="PAK device is inactive or archived.")

        await self.record_seen(pak)

        return pak

    async def record_seen(self, pak: m.PakDevice) -> None:
        """Record that the device reached the API now, in a transaction of its own.

        The request's transaction may still roll back; the device was seen
        either way. Concurrent requests keep the latest time.
        """
        engine = self.repository.session.bind

        if not isinstance(engine, AsyncEngine):
            msg = "Recording PAK presence needs a session bound to an engine."
            raise TypeError(msg)

        seen = insert(m.PakDevicePresence).values(pak_id=pak.id, last_seen_at=datetime.now(UTC))
        upsert = seen.on_conflict_do_update(
            index_elements=[m.PakDevicePresence.pak_id],
            set_={"last_seen_at": func.greatest(m.PakDevicePresence.last_seen_at, seen.excluded.last_seen_at)},
        ).returning(m.PakDevicePresence.last_seen_at)

        async with engine.begin() as connection:
            last_seen_at = (await connection.execute(upsert)).scalar_one()

        set_committed_value(pak, "last_seen_at", last_seen_at)

    async def _require(
        self,
        pak_id: UUID,
        *,
        for_update: bool = False,
    ) -> m.PakDevice:
        pak = await self.get_by_id(pak_id, for_update=for_update)

        if pak is None:
            raise NotFoundError("PAK device not found.")

        return pak

    async def _ensure_unique_code(self, code: object) -> None:
        if isinstance(code, str) and await self.get_by_code(code) is not None:
            raise PakDeviceCodeTakenError
