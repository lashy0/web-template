from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from advanced_alchemy.exceptions import IntegrityError, NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import exists, select

from app.db import models as m
from app.domain.production.exceptions import (
    KgVersionArchivedError,
    KgVersionCodeTakenError,
    KgVersionInUseError,
)


class KgVersionService(service.SQLAlchemyAsyncRepositoryService[m.KgVersion]):
    """Application service for the KG version catalog."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.KgVersion]):
        """KG version SQLAlchemy repository."""

        model_type = m.KgVersion

    repository_type = Repo

    async def create_version(self, data: dict[str, object]) -> m.KgVersion:
        if await self.exists(code=data["code"]):
            raise KgVersionCodeTakenError

        try:
            return await self.create(data, auto_commit=False)
        except IntegrityError as error:
            raise KgVersionCodeTakenError from error

    async def update_version(
        self,
        version_id: UUID,
        data: dict[str, object],
    ) -> m.KgVersion:
        version = await self._require(version_id, for_update=True)

        if version.archived_at is not None:
            raise KgVersionArchivedError

        return await self.update(
            data,
            item_id=version_id,
            auto_commit=False,
        )

    async def set_archived(
        self,
        version_id: UUID,
        *,
        archived: bool,
    ) -> m.KgVersion:
        """Archive or restore a version; repeating the request keeps the original archive time."""
        version = await self._require(version_id, for_update=True)

        if archived and version.archived_at is None:
            version.archived_at = datetime.now(UTC)
        elif not archived:
            version.archived_at = None

        await self.repository.session.flush()

        return version

    async def delete_version(self, version_id: UUID) -> m.KgVersion:
        version = await self._require(version_id, for_update=True)

        if await self.repository.session.scalar(
            select(
                exists().where(
                    m.Batch.kg_version_id == version.id
                )
            )
        ):
            raise KgVersionInUseError

        await self.repository.session.delete(version)
        await self.repository.session.flush()

        return version

    async def _require(
        self,
        version_id: UUID,
        *,
        for_update: bool = False,
    ) -> m.KgVersion:
        version = await self.get_one_or_none(
            m.KgVersion.id == version_id,
            with_for_update=for_update,
        )

        if version is None:
            raise NotFoundError("KG version not found.")

        return version
