from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from advanced_alchemy.exceptions import IntegrityError, NotFoundError
from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m
from app.domain.production.exceptions import (
    KgPrefixArchivedError,
    KgPrefixInUseError,
    KgPrefixShortCodeTakenError,
    KgPrefixTakenError,
)
from app.lib.exceptions import ApplicationConflictError


class KgPrefixService(service.SQLAlchemyAsyncRepositoryService[m.KgPrefix]):
    """Application service for the DevEUI prefix catalog."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.KgPrefix]):
        """DevEUI prefix SQLAlchemy repository."""

        model_type = m.KgPrefix

    repository_type = Repo

    async def create_prefix(self, data: dict[str, object]) -> m.KgPrefix:
        if await self.exists(prefix=data["prefix"]):
            raise KgPrefixTakenError

        if await self.exists(short_code=data["short_code"]):
            raise KgPrefixShortCodeTakenError

        try:
            return await self.create(data, auto_commit=False)
        except IntegrityError as error:
            # A concurrent request took one of the values after the checks above;
            # the violated constraint is not reported portably, so no code.
            raise ApplicationConflictError(
                detail="DevEUI prefix or short code is already registered.",
            ) from error

    async def update_prefix(
        self,
        prefix_id: UUID,
        data: dict[str, object],
    ) -> m.KgPrefix:
        prefix = await self._require(prefix_id, for_update=True)

        if prefix.archived_at is not None:
            raise KgPrefixArchivedError

        return await self.update(
            data,
            item_id=prefix_id,
            auto_commit=False,
        )

    async def set_archived(
        self,
        prefix_id: UUID,
        *,
        archived: bool,
    ) -> m.KgPrefix:
        """Archive or restore a prefix; repeating the request keeps the original archive time."""
        prefix = await self._require(prefix_id, for_update=True)

        if archived and prefix.archived_at is None:
            prefix.archived_at = datetime.now(UTC)
        elif not archived:
            prefix.archived_at = None

        await self.repository.session.flush()

        return prefix

    async def delete_prefix(self, prefix_id: UUID) -> m.KgPrefix:
        prefix = await self._require(prefix_id, for_update=True)

        # Deleting the row would reset its counter and reissue the DevEUIs.
        if prefix.next_serial > 1:
            raise KgPrefixInUseError

        await self.repository.session.delete(prefix)
        await self.repository.session.flush()

        return prefix

    async def _require(
        self,
        prefix_id: UUID,
        *,
        for_update: bool = False,
    ) -> m.KgPrefix:
        prefix = await self.get_one_or_none(
            m.KgPrefix.id == prefix_id,
            with_for_update=for_update,
            # A locked read must replace what an earlier read left in the session.
            execution_options={"populate_existing": for_update},
        )

        if prefix is None:
            raise NotFoundError("DevEUI prefix not found.")

        return prefix
