from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import models as m
from app.lib.audit import change_details, snapshot

logger = structlog.get_logger()

_AUDIT_FIELDS = {"defect_group_code": "defect_group_code", "defect_group": "defect_group.name"}
"""The group is recorded by name: a check can move to another group with the same code."""


@dataclass(frozen=True, slots=True)
class CheckObservation:
    """What a PAK report changed in the check catalog."""

    check: m.PakCheck
    created: bool = False
    changes: dict[str, Any] = field(default_factory=dict[str, Any])
    """Changed fields as ``{field: {"from": old, "to": new}}``, for the audit log."""


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

        before = snapshot(check, _AUDIT_FIELDS)
        group_changed = check.defect_group_id != group_id
        check.defect_group_code = defect_group_code
        check.defect_group_id = group_id
        check.last_seen_at = max(check.last_seen_at, seen_at)
        await self.repository.session.flush()

        if group_changed:
            await self.repository.session.refresh(check, attribute_names=("defect_group",))

        details = change_details(before, snapshot(check, _AUDIT_FIELDS))
        return CheckObservation(check=check, changes=details["changes"] if details else {})

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
