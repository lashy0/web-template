from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.modules.kg.models import KgStatus, KgUnit
from app.modules.kg.repository import KgRepository
from app.modules.pak.models import PakDevice
from app.modules.pak.service import PakTestCatalogService
from app.modules.verification.exceptions import (
    VerificationKgNotFoundError,
    VerificationKgNotReadyError,
    VerificationSessionAlreadyRunningError,
    VerificationSessionIncompleteError,
    VerificationSessionNotFoundError,
    VerificationSessionNotRunningError,
    VerificationStepAlreadyCompletedError,
    VerificationStepAlreadyExistsError,
    VerificationStepInProgressError,
    VerificationStepNotFoundError,
    VerificationStepOutOfRangeError,
)
from app.modules.verification.models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)
from app.modules.verification.repository import (
    VerificationSessionRepository,
    VerificationStepRepository,
)


DEFAULT_REOPEN_INACTIVITY_MINUTES = 60
DEFAULT_SESSION_TTL_MINUTES = 120


class VerificationManagementService:
    """Coordinates PAK verification sessions and KG state."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        reopen_inactivity_minutes: int = DEFAULT_REOPEN_INACTIVITY_MINUTES,
        session_ttl_minutes: int = DEFAULT_SESSION_TTL_MINUTES,
    ) -> None:
        if reopen_inactivity_minutes <= 0:
            raise ValueError(
                "reopen_inactivity_minutes must be positive"
            )

        if session_ttl_minutes <= 0:
            raise ValueError(
                "session_ttl_minutes must be positive"
            )

        if reopen_inactivity_minutes >= session_ttl_minutes:
            raise ValueError(
                "reopen_inactivity_minutes must be less than session_ttl_minutes"
            )

        self._session_factory = session_factory

        self._pak_test_catalog = PakTestCatalogService(session_factory)

        self._reopen_inactivity = timedelta(minutes=reopen_inactivity_minutes)
        self._session_ttl = timedelta(minutes=session_ttl_minutes)

    async def get(self, session_id: UUID) -> VerificationSession | None:
        async with self._session_factory() as session:
            return await VerificationSessionRepository(session).get_by_id(session_id)

    async def get_detail(
        self,
        session_id: UUID,
    ) -> tuple[
        VerificationSession,
        list[VerificationStep],
    ] | None:
        async with self._session_factory() as session:
            verification_session = await VerificationSessionRepository(
                session
            ).get_by_id(session_id)

            if verification_session is None:
                return None

            steps = await VerificationStepRepository(
                session
            ).list_by_session(verification_session.id)

            return verification_session, steps

    async def list(self, **filters: object) -> tuple[list[VerificationSession], int]:
        async with self._session_factory() as session:
            return await VerificationSessionRepository(
                session
            ).search(**filters) # type: ignore[arg-type]

    # PAK lifecycle

    async def open_session(
        self,
        *,
        pak: PakDevice,
        kg_dev_eui: str,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> VerificationSession:
        now = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            verification_repository = VerificationSessionRepository(session)
            step_repository = VerificationStepRepository(session)
            kg_repository = KgRepository(session)

            await verification_repository.lock_session_open(
                kg_dev_eui=kg_dev_eui,
                pak_id=pak.id,
                slot_no=slot_no,
            )

            kg = await kg_repository.get_by_dev_eui(kg_dev_eui)

            if kg is None:
                raise VerificationKgNotFoundError

            running_by_kg = await verification_repository.get_running_by_kg(kg.dev_eui)

            if running_by_kg is not None:
                same_location = (
                    running_by_kg.pak_id == pak.id
                    and running_by_kg.slot_no == slot_no
                )

                if self._is_reopen_stale(running_by_kg, now=now):
                    await self._close_incomplete(
                        verification_repository,
                        step_repository,
                        kg_repository,
                        running_by_kg,
                        completed_at=now,
                    )

                elif same_location:
                    # Idempotent open retry
                    await verification_repository.touch_activity(
                        running_by_kg,
                        at=now,
                    )

                    return running_by_kg

                else:
                    # The same KG is actively being tested somewhere else
                    raise VerificationSessionAlreadyRunningError

            # Re-read after a stale KG session may have been closed above
            running_by_slot = (
                await verification_repository
                .get_running_by_pak_slot(
                    pak_id=pak.id,
                    slot_no=slot_no,
                )
            )

            if running_by_slot is not None:
                # A new KG appearing in the same physical
                # slot means the previous run was not completed correctly
                await self._close_incomplete(
                    verification_repository,
                    step_repository,
                    kg_repository,
                    running_by_slot,
                    completed_at=now,
                )

            self._ensure_kg_ready(kg)

            verification_session = (
                await verification_repository.create(
                    kg_dev_eui=kg.dev_eui,
                    pak_id=pak.id,
                    slot_no=slot_no,
                    firmware_version=firmware_version,
                    total_steps=total_steps,
                )
            )

            await kg_repository.update_status(kg, status=KgStatus.TESTING)

            return verification_session

    async def start_step(
        self,
        *,
        pak: PakDevice,
        session_id: UUID,
        step_no: int,
        test_name: str,
        test_label: str,
        error_group_code: str,
    ) -> VerificationStep:
        now = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            verification_repository = VerificationSessionRepository(session)
            step_repository = VerificationStepRepository(session)

            verification_session = await self._required_session_for_update(
                verification_repository,
                session_id,
            )

            self._ensure_session_owned_by_pak(verification_session, pak)
            self._ensure_session_running(verification_session)
            self._ensure_step_in_range(verification_session, step_no)

            existing = await step_repository.get_by_session_and_step_no(
                session_id=verification_session.id,
                step_no=step_no,
            )

            if existing is not None:
                if (
                    existing.test_name == test_name
                    and existing.test_label == test_label
                    and existing.error_group_code == error_group_code
                ):
                    # Safe retry of the same start request
                    await verification_repository.touch_activity(
                        verification_session,
                        at=now,
                    )

                    return existing

                raise VerificationStepAlreadyExistsError

            if await step_repository.exists_running_by_session(verification_session.id):
                raise VerificationStepInProgressError

            pak_test = await self._pak_test_catalog.observe_in_session(
                session,
                pak=pak,
                test_name=test_name,
                test_label=test_label,
                defect_group_code=error_group_code,
                seen_at=now,
            )

            step = await step_repository.create(
                session_id=verification_session.id,
                step_no=step_no,
                pak_test_id=pak_test.id,
                defect_group_id=pak_test.defect_group_id,
                test_name=test_name,
                test_label=test_label,
                error_group_code=error_group_code,
            )

            await verification_repository.touch_activity(
                verification_session,
                at=now,
            )

            return step

    async def complete_step(
        self,
        *,
        pak: PakDevice,
        session_id: UUID,
        step_no: int,
        status: VerificationStepStatus,
        measurement_value: float | None,
        measurement_min_value: float | None,
        measurement_max_value: float | None,
        measurement_unit: str | None,
    ) -> VerificationStep:
        if status not in {
            VerificationStepStatus.PASSED,
            VerificationStepStatus.FAILED,
        }:
            raise ValueError(
                "PAK may complete a step only with PASSED or FAILED status"
            )

        now = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            verification_repository = VerificationSessionRepository(session)
            step_repository = VerificationStepRepository(session)

            verification_session = await self._required_session_for_update(
                verification_repository,
                session_id,
            )

            self._ensure_session_owned_by_pak(verification_session, pak)
            self._ensure_session_running(verification_session)
            self._ensure_step_in_range(verification_session, step_no)

            step = await step_repository.get_by_session_and_step_no_for_update(
                session_id=verification_session.id,
                step_no=step_no,
            )

            if step is None:
                raise VerificationStepNotFoundError

            if step.status != VerificationStepStatus.RUNNING:
                if self._same_step_result(
                    step,
                    status=status,
                    measurement_value=measurement_value,
                    measurement_min_value=measurement_min_value,
                    measurement_max_value=measurement_max_value,
                    measurement_unit=measurement_unit,
                ):
                    # Response may have been lost and PAK repeated the same request
                    await verification_repository.touch_activity(
                        verification_session,
                        at=now,
                    )

                    return step

                raise VerificationStepAlreadyCompletedError

            step = await step_repository.complete(
                step,
                status=status,
                measurement_value=measurement_value,
                measurement_min_value=measurement_min_value,
                measurement_max_value=measurement_max_value,
                measurement_unit=measurement_unit,
                completed_at=now,
            )

            await verification_repository.touch_activity(
                verification_session,
                at=now,
            )

            return step

    async def complete_session(
        self,
        *,
        pak: PakDevice,
        session_id: UUID,
        status: VerificationSessionStatus,
    ) -> VerificationSession:
        if status not in {
            VerificationSessionStatus.PASSED,
            VerificationSessionStatus.FAILED,
            VerificationSessionStatus.ABORTED,
        }:
            raise ValueError(
                "PAK may complete a session only with PASSED, FAILED or ABORTED status"
            )

        now = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            verification_repository = VerificationSessionRepository(session)
            step_repository = VerificationStepRepository(session)
            kg_repository = KgRepository(session)

            verification_session = await self._required_session_for_update(
                verification_repository,
                session_id,
            )

            self._ensure_session_owned_by_pak(verification_session, pak)

            if verification_session.status != VerificationSessionStatus.RUNNING:
                if verification_session.status == status:
                    # Idempotent completion retry
                    return verification_session

                raise VerificationSessionNotRunningError

            running_step = await step_repository.get_running_by_session_for_update(
                verification_session.id
            )

            if running_step is not None:
                if status != VerificationSessionStatus.ABORTED:
                    raise VerificationSessionIncompleteError

                await self._abort_step(
                    step_repository,
                    running_step,
                    completed_at=now,
                )

            if status == VerificationSessionStatus.PASSED:
                passed_steps = await step_repository.count_by_session_and_status(
                    session_id=verification_session.id,
                    status=VerificationStepStatus.PASSED
                )

                if passed_steps != verification_session.total_steps:
                    raise VerificationSessionIncompleteError

            kg = await kg_repository.get_by_dev_eui(verification_session.kg_dev_eui)

            if kg is None:
                raise VerificationKgNotFoundError

            if kg.status != KgStatus.TESTING:
                raise VerificationKgNotReadyError

            verification_session = await verification_repository.complete(
                verification_session,
                status=status,
                completed_at=now,
            )

            await kg_repository.update_status(
                kg,
                status=self._kg_status_after_completion(status),
            )

            return verification_session

    # Background stale cleanup

    async def expire_stale_sessions(
        self,
        *,
        batch_size: int = 100,
    ) -> int:
        if batch_size <= 0:
            raise ValueError(
                "batch_size must be positive"
            )

        total_expired = 0

        while True:
            now = datetime.now(UTC)
            cutoff = now - self._session_ttl

            async with self._session_factory() as session, session.begin():
                verification_repository = VerificationSessionRepository(session)
                step_repository = VerificationStepRepository(session)
                kg_repository = KgRepository(session)

                stale_sessions = await verification_repository.list_stale_running_for_update(
                    cutoff=cutoff,
                    limit=batch_size,
                )

                if not stale_sessions:
                    return total_expired

                for verification_session in stale_sessions:
                    await self._close_incomplete(
                        verification_repository,
                        step_repository,
                        kg_repository,
                        verification_session,
                        completed_at=now,
                    )

                expired_count = len(stale_sessions)
                total_expired += expired_count

            if expired_count < batch_size:
                return total_expired

    # Internal lifecycle

    async def _close_incomplete(
        self,
        verification_repository: VerificationSessionRepository,
        step_repository: VerificationStepRepository,
        kg_repository: KgRepository,
        verification_session: VerificationSession,
        *,
        completed_at: datetime,
    ) -> None:
        if verification_session.status != VerificationSessionStatus.RUNNING:
            return

        running_step = await step_repository.get_running_by_session_for_update(
            verification_session.id
        )

        if running_step is not None:
            await self._abort_step(
                step_repository,
                running_step,
                completed_at=completed_at,
            )

        await verification_repository.complete(
            verification_session,
            status=VerificationSessionStatus.INCOMPLETE,
            completed_at=completed_at,
        )

        kg = await kg_repository.get_by_dev_eui(verification_session.kg_dev_eui)

        if kg is not None and kg.status == KgStatus.TESTING:
            await kg_repository.update_status(kg, status=KgStatus.READY_FOR_RETEST)

    @staticmethod
    async def _abort_step(
        repository: VerificationStepRepository,
        step: VerificationStep,
        *,
        completed_at: datetime,
    ) -> VerificationStep:
        return await repository.complete(
            step,
            status=VerificationStepStatus.ABORTED,
            measurement_value=step.measurement_value,
            measurement_min_value=step.measurement_min_value,
            measurement_max_value=step.measurement_max_value,
            measurement_unit=step.measurement_unit,
            completed_at=completed_at,
        )

    # Helpers

    async def _required_session_for_update(
        self,
        repository: VerificationSessionRepository,
        session_id: UUID,
    ) -> VerificationSession:
        verification_session = await repository.get_by_id_for_update(session_id)

        if verification_session is None:
            raise VerificationSessionNotFoundError

        return verification_session

    @staticmethod
    def _ensure_session_owned_by_pak(
        verification_session: VerificationSession,
        pak: PakDevice,
    ) -> None:
        if verification_session.pak_id != pak.id:
            # Do not expose another PAK's session
            raise VerificationSessionNotFoundError

    @staticmethod
    def _ensure_session_running(verification_session: VerificationSession) -> None:
        if verification_session.status != VerificationSessionStatus.RUNNING:
            raise VerificationSessionNotRunningError

    @staticmethod
    def _ensure_step_in_range(
        verification_session: VerificationSession,
        step_no: int,
    ) -> None:
        if not (1 <= step_no <= verification_session.total_steps):
            raise VerificationStepOutOfRangeError

    @staticmethod
    def _ensure_kg_ready(kg: KgUnit) -> None:
        if kg.status not in {
            KgStatus.REGISTERED,
            KgStatus.READY_FOR_RETEST,
        }:
            raise VerificationKgNotReadyError

    def _is_reopen_stale(
        self,
        verification_session: VerificationSession,
        *,
        now: datetime,
    ) -> bool:
        return (
            now - verification_session.last_activity_at
            >= self._reopen_inactivity
        )

    @staticmethod
    def _kg_status_after_completion(status: VerificationSessionStatus) -> KgStatus:
        if status == VerificationSessionStatus.PASSED:
            return KgStatus.READY_FOR_PACKING

        if status == VerificationSessionStatus.FAILED:
            return KgStatus.TEST_FAILED

        if status == VerificationSessionStatus.ABORTED:
            return KgStatus.READY_FOR_RETEST

        raise ValueError(
            "Unsupported verification completion status"
        )

    @staticmethod
    def _same_step_result(
        step: VerificationStep,
        *,
        status: VerificationStepStatus,
        measurement_value: float | None,
        measurement_min_value: float | None,
        measurement_max_value: float | None,
        measurement_unit: str | None,
    ) -> bool:
        return (
            step.status == status
            and step.measurement_value
            == measurement_value
            and step.measurement_min_value
            == measurement_min_value
            and step.measurement_max_value
            == measurement_max_value
            and step.measurement_unit
            == measurement_unit
        )
