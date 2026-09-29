from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.exceptions import IntegrityError, NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import select

from app.db import models as m
from app.domain.quality.exceptions import (
    DefectGroupArchivedError,
    DefectTypeArchivedError,
    DefectTypeCodeTakenError,
)

if TYPE_CHECKING:
    from app.domain.quality import schemas as s


class DefectTypeService(service.SQLAlchemyAsyncRepositoryService[m.DefectType]):
    """Application service for defect types."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.DefectType]):
        """Defect type SQLAlchemy repository."""

        model_type = m.DefectType

    repository_type = Repo

    async def create_type(self, data: s.DefectTypeCreate) -> m.DefectType:
        await self._ensure_active_group(
            data.group_id,
            detail="Archived defect group cannot receive defect types.",
        )

        if await self.exists(code=data.code):
            raise DefectTypeCodeTakenError

        try:
            defect_type = await self.create(data.to_dict(), auto_commit=False)
        except IntegrityError as error:
            raise DefectTypeCodeTakenError from error

        await self.repository.session.refresh(defect_type, attribute_names=("group",))

        return defect_type

    async def update_type(self, type_id: UUID, data: dict[str, object]) -> m.DefectType:
        defect_type = await self._require(type_id, for_update=True)

        if defect_type.archived_at is not None:
            raise DefectTypeArchivedError

        for field, value in data.items():
            setattr(defect_type, field, value)

        await self.repository.session.flush()

        return defect_type

    async def set_archived(self, type_id: UUID, *, archived: bool) -> m.DefectType:
        """Archive or restore a type; repeating the request keeps the original archive time.

        A type is restored only into an active group.
        """
        defect_type = await self._require(type_id, for_update=True)

        if archived and defect_type.archived_at is None:
            defect_type.archived_at = datetime.now(UTC)
        elif not archived and defect_type.archived_at is not None:
            await self._ensure_active_group(
                defect_type.group_id,
                detail="Restore the defect group before its defect types.",
            )
            defect_type.archived_at = None

        await self.repository.session.flush()

        return defect_type

    async def delete_type(self, type_id: UUID) -> m.DefectType:
        defect_type = await self._require(type_id, for_update=True)

        await self.repository.session.delete(defect_type)
        await self.repository.session.flush()

        return defect_type

    async def _ensure_active_group(self, group_id: UUID, *, detail: str) -> None:
        # A shared lock keeps the group from being archived before the type commits.
        group: m.DefectGroup | None = await self.repository.session.scalar(
            select(m.DefectGroup)
            .where(m.DefectGroup.id == group_id)
            .with_for_update(read=True, of=m.DefectGroup)
            .execution_options(populate_existing=True)
        )

        if group is None:
            raise NotFoundError("Defect group not found.")

        if group.archived_at is not None:
            raise DefectGroupArchivedError(detail=detail)

    async def _require(self, type_id: UUID, *, for_update: bool = False) -> m.DefectType:
        defect_type = await self.get_one_or_none(
            m.DefectType.id == type_id,
            with_for_update=for_update,
            # A locked read must replace what an earlier read left in the session.
            execution_options={"populate_existing": for_update},
        )

        if defect_type is None:
            raise NotFoundError("Defect type not found.")

        return defect_type
