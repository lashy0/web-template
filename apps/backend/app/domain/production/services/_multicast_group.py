from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from advanced_alchemy.exceptions import IntegrityError, NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import exists, or_, select

from app.db import models as m
from app.domain.production.exceptions import (
    MulticastGroupArchivedError,
    MulticastGroupInUseError,
    MulticastGroupNameTakenError,
)
from app.domain.production.schemas import MulticastGroupKeys
from app.lib.concurrency import ensure_unchanged
from app.lib.exceptions import ApplicationConflictError
from app.lib.lorawan import generate_multicast_address, generate_multicast_key

_ADDRESS_ATTEMPTS = 10
"""Random addresses tried before giving up; four bytes make a repeat unlikely."""

_RADIO_FIELDS = frozenset({"group_id", "frequency_hz", "datarate"})
"""Fields the KG units of a batch were provisioned with."""


class MulticastGroupService(service.SQLAlchemyAsyncRepositoryService[m.MulticastGroup]):
    """Application service for the multicast group catalog."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.MulticastGroup]):
        """Multicast group SQLAlchemy repository."""

        model_type = m.MulticastGroup

    repository_type = Repo

    async def create_group(self, data: dict[str, object]) -> m.MulticastGroup:
        """Register a group with a generated address unused by other groups and a new McKey."""
        if await self.exists(name=data["name"]):
            raise MulticastGroupNameTakenError

        try:
            return await self.create(
                {**data, "mc_addr": await self._free_address(), "mc_key": generate_multicast_key()},
                auto_commit=False,
            )
        except IntegrityError as error:
            # A concurrent request took the name or the address after the checks above;
            # the violated constraint is not reported portably, so no code.
            raise ApplicationConflictError(detail="Multicast group name or address is already registered.") from error

    async def update_group(
        self,
        multicast_group_id: UUID,
        data: dict[str, object],
        *,
        expected_updated_at: datetime | None = None,
    ) -> m.MulticastGroup:
        group = await self._require(multicast_group_id, for_update=True)
        ensure_unchanged(group, expected_updated_at)

        if group.archived_at is not None:
            raise MulticastGroupArchivedError

        changed = {field for field, value in data.items() if getattr(group, field) != value}

        if changed & _RADIO_FIELDS and await self._in_use(group.id):
            raise MulticastGroupInUseError

        if "name" in changed and await self.exists(name=data["name"]):
            raise MulticastGroupNameTakenError

        try:
            return await self.update(data, item_id=multicast_group_id, auto_commit=False)
        except IntegrityError as error:
            raise MulticastGroupNameTakenError from error

    async def set_archived(self, multicast_group_id: UUID, *, archived: bool) -> m.MulticastGroup:
        """Archive or restore a group; repeating the request keeps the original archive time."""
        group = await self._require(multicast_group_id, for_update=True)

        if archived and group.archived_at is None:
            group.archived_at = datetime.now(UTC)
        elif not archived:
            group.archived_at = None

        await self.repository.session.flush()

        return group

    async def delete_group(self, multicast_group_id: UUID) -> m.MulticastGroup:
        group = await self._require(multicast_group_id, for_update=True)

        if await self._in_use(group.id):
            raise MulticastGroupInUseError

        await self.repository.session.delete(group)
        await self.repository.session.flush()

        return group

    async def get_keys(self, multicast_group_id: UUID) -> MulticastGroupKeys:
        """The McKey of the group and the session keys derived from it."""
        group = await self._require(multicast_group_id)
        session_keys = group.session_keys

        return MulticastGroupKeys(
            mc_key=group.mc_key,
            mc_nwk_s_key=session_keys.mc_nwk_s_key,
            mc_app_s_key=session_keys.mc_app_s_key,
        )

    async def _free_address(self) -> str:
        for _ in range(_ADDRESS_ATTEMPTS):
            address = generate_multicast_address()

            if not await self.exists(mc_addr=address):
                return address

        raise ApplicationConflictError(detail="No free multicast address was found; try again.")

    async def _in_use(self, multicast_group_id: UUID) -> bool:
        return bool(
            await self.repository.session.scalar(
                select(
                    exists().where(
                        or_(
                            m.Batch.multicast_group_0_id == multicast_group_id,
                            m.Batch.multicast_group_1_id == multicast_group_id,
                        )
                    )
                )
            )
        )

    async def _require(self, multicast_group_id: UUID, *, for_update: bool = False) -> m.MulticastGroup:
        group = await self.get_one_or_none(
            m.MulticastGroup.id == multicast_group_id,
            with_for_update=for_update,
            # A locked read must replace what an earlier read left in the session.
            execution_options={"populate_existing": for_update},
        )

        if group is None:
            raise NotFoundError("Multicast group not found.")

        return group
