from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from advanced_alchemy.exceptions import IntegrityError, NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import exists, select

from app.db import models as m
from app.domain.quality.exceptions import (
    DefectGroupArchivedError,
    DefectGroupCodeTakenError,
    DefectGroupHasActiveTypesError,
    DefectGroupInUseError,
)

_TYPE_COUNTS = ("types_count", "active_types_count")


class DefectGroupService(service.SQLAlchemyAsyncRepositoryService[m.DefectGroup]):
    """Application service for defect groups."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.DefectGroup]):
        """Defect group SQLAlchemy repository."""

        model_type = m.DefectGroup

    repository_type = Repo

    async def create_group(self, data: dict[str, object]) -> m.DefectGroup:
        if await self.exists(code=data["code"]):
            raise DefectGroupCodeTakenError

        try:
            group = await self.create(data, auto_commit=False)
        except IntegrityError as error:
            raise DefectGroupCodeTakenError from error

        await self.repository.session.refresh(group, attribute_names=_TYPE_COUNTS)

        return group

    async def update_group(self, group_id: UUID, data: dict[str, object]) -> m.DefectGroup:
        group = await self._require(group_id, for_update=True)

        if group.archived_at is not None:
            raise DefectGroupArchivedError

        for field, value in data.items():
            setattr(group, field, value)

        await self.repository.session.flush()

        return group

    async def set_archived(self, group_id: UUID, *, archived: bool) -> m.DefectGroup:
        """Archive or restore a group; repeating the request keeps the original archive time.

        A group is archived only after all of its types; the row lock keeps a
        type from being added or restored meanwhile.
        """
        group = await self._require(group_id, for_update=True)

        if archived and group.archived_at is None:
            active_types = select(m.DefectType).where(
                m.DefectType.group_id == group.id,
                m.DefectType.archived_at.is_(None),
            )

            if await self.repository.session.scalar(select(exists(active_types))):
                raise DefectGroupHasActiveTypesError

            group.archived_at = datetime.now(UTC)
        elif not archived:
            group.archived_at = None

        await self.repository.session.flush()

        return group

    async def delete_group(self, group_id: UUID) -> m.DefectGroup:
        group = await self._require(group_id, for_update=True)

        references = (
            exists().where(m.DefectType.group_id == group.id)
            | exists().where(m.PakCheck.defect_group_id == group.id)
            | exists().where(m.VerificationStep.defect_group_id == group.id)
        )

        if await self.repository.session.scalar(select(references)):
            raise DefectGroupInUseError

        await self.repository.session.delete(group)
        await self.repository.session.flush()

        return group

    async def _require(self, group_id: UUID, *, for_update: bool = False) -> m.DefectGroup:
        group = await self.get_one_or_none(
            m.DefectGroup.id == group_id,
            with_for_update=for_update,
            # A locked read must replace what an earlier read left in the session.
            execution_options={"populate_existing": for_update},
        )

        if group is None:
            raise NotFoundError("Defect group not found.")

        return group
