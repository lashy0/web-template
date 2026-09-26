from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import models as m

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class CheckObservation:
    """What a PAK report changed in the check catalog."""

    check: m.PakCheck
    created: bool = False
    changes: dict[str, Any] = field(default_factory=dict[str, Any])
    """Changed fields with their previous and new values, for the audit log."""


class PakCheckService(service.SQLAlchemyAsyncRepositoryService[m.PakCheck]):
    """The catalog of checks as PAKs report them; users only read it."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.PakCheck]):
        """PAK check SQLAlchemy repository."""

        model_type = m.PakCheck

    repository_type = Repo

    async def observe(
        self,
        *,
        pak: m.PakDevice,
        name: str,
        label: str,
        defect_group_code: str,
        seen_at: datetime,
    ) -> CheckObservation:
        """Record a check a PAK is starting, creating or updating its catalog entry.

        A check is identified by its name and label together. A defect group
        code that matches no active group is accepted: the check is kept
        without a group and shows as misconfigured until a PAK reports it
        again with a known code.
        """
        group = await self._lock_active_group(defect_group_code)
        group_id = group.id if group is not None else None

        if group is None:
            logger.warning(
                "pak_check.unknown_defect_group",
                pak_id=str(pak.id),
                pak_code=pak.code,
                check_name=name,
                check_label=label,
                defect_group_code=defect_group_code,
            )

        check = await self._lock_check(name, label)

        if check is None:
            inserted = await self.repository.session.scalar(
                insert(m.PakCheck)
                .values(
                    name=name,
                    label=label,
                    defect_group_code=defect_group_code,
                    defect_group_id=group_id,
                    last_seen_at=seen_at,
                )
                .on_conflict_do_nothing(index_elements=[m.PakCheck.name, m.PakCheck.label])
                .returning(m.PakCheck.id)
            )

            # Another PAK may have added the check since the lookup; update that row instead.
            check = await self._lock_check(name, label)

            if check is None:
                msg = f"PAK check {name!r} ({label!r}) vanished after it was recorded."
                raise LookupError(msg)

            if inserted is not None:
                return CheckObservation(check=check, created=True)

        changes: dict[str, Any] = {}

        for attribute, value in (
            ("defect_group_code", defect_group_code),
            ("defect_group_id", group_id),
        ):
            previous = getattr(check, attribute)

            if previous != value:
                changes[attribute] = {"old": _audit_value(previous), "new": _audit_value(value)}
                setattr(check, attribute, value)

        check.last_seen_at = max(check.last_seen_at, seen_at)
        await self.repository.session.flush()

        if "defect_group_id" in changes:
            await self.repository.session.refresh(check, attribute_names=("defect_group",))

        return CheckObservation(check=check, changes=changes)

    async def _lock_active_group(self, code: str) -> m.DefectGroup | None:
        # A shared lock keeps the group from being archived or deleted before the check commits.
        group: m.DefectGroup | None = await self.repository.session.scalar(
            select(m.DefectGroup)
            .where(m.DefectGroup.code == code)
            .with_for_update(read=True, of=m.DefectGroup)
            .execution_options(populate_existing=True)
        )

        if group is None or group.archived_at is not None:
            return None

        return group

    async def _lock_check(self, name: str, label: str) -> m.PakCheck | None:
        return await self.get_one_or_none(
            m.PakCheck.name == name,
            m.PakCheck.label == label,
            with_for_update=True,
            # A locked read must replace what an earlier read left in the session.
            execution_options={"populate_existing": True},
        )


def _audit_value(value: object) -> object:
    return None if value is None else str(value)
