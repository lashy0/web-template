from datetime import UTC, datetime, timedelta

from ..contracts import VerificationKgPort, VerificationPakPort
from ..exceptions import VerificationKgNotFoundError, VerificationSessionAlreadyRunningError
from ..model import VerificationSession
from ..repository import VerificationRepository
from ..rules import is_reopen_stale
from .complete import close_incomplete


class StartVerificationSession:
    def __init__(
        self,
        repository: VerificationRepository,
        kg: VerificationKgPort,
        *,
        reopen_inactivity: timedelta,
    ) -> None:
        self._repository = repository
        self._kg = kg
        self._reopen_inactivity = reopen_inactivity

    async def execute(
        self,
        *,
        pak: VerificationPakPort,
        kg_dev_eui: str,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> VerificationSession:
        # PostgreSQL transaction locks are deliberately ordered KG -> PAK slot.
        await self._repository.lock_open_keys(kg_dev_eui=kg_dev_eui, pak_id=pak.id, slot_no=slot_no)
        candidates = await self._repository.lock_running_candidates(
            kg_dev_eui=kg_dev_eui, pak_id=pak.id, slot_no=slot_no
        )
        kg = await self._kg.resolve_and_lock(
            dev_eui=kg_dev_eui, related_dev_euis=[item.kg_dev_eui for item in candidates]
        )
        if kg is None:
            raise VerificationKgNotFoundError
        now = datetime.now(UTC)
        by_kg = await self._repository.get_running_by_kg(kg.dev_eui)
        if by_kg is not None:
            same_location = by_kg.pak_id == pak.id and by_kg.slot_no == slot_no
            if is_reopen_stale(by_kg, now=now, reopen_inactivity=self._reopen_inactivity):
                await close_incomplete(self._repository, by_kg, completed_at=now)
            elif same_location:
                return await self._repository.touch_session(by_kg, at=now)
            else:
                raise VerificationSessionAlreadyRunningError
        by_slot = await self._repository.get_running_by_pak_slot(pak_id=pak.id, slot_no=slot_no)
        if by_slot is not None:
            await close_incomplete(self._repository, by_slot, completed_at=now)
        if kg.state != "REGISTERED":
            # The public error conversion is intentionally owned by the command.
            from ..exceptions import VerificationKgNotReadyError

            raise VerificationKgNotReadyError
        return await self._repository.create_session(
            kg_dev_eui=kg.dev_eui,
            pak_id=pak.id,
            slot_no=slot_no,
            firmware_version=firmware_version,
            total_steps=total_steps,
        )
