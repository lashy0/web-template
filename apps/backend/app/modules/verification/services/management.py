from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.pak.models import PakDevice
from app.modules.pak.services import PakTestCatalogService

from ..models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)
from .cleanup import VerificationCleanupService
from .session import (
    VerificationSessionService as VerificationSessionService,
)
from .step import VerificationStepService
from .transactions import transaction

DEFAULT_REOPEN_INACTIVITY_MINUTES = 60
DEFAULT_SESSION_TTL_MINUTES = 120


class VerificationManagementService:
    """Compatibility API gateway: session ownership and service dispatch only."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        reopen_inactivity_minutes: int = DEFAULT_REOPEN_INACTIVITY_MINUTES,
        session_ttl_minutes: int = DEFAULT_SESSION_TTL_MINUTES,
    ) -> None:
        if reopen_inactivity_minutes <= 0:
            raise ValueError("reopen_inactivity_minutes must be positive")

        if session_ttl_minutes <= 0:
            raise ValueError("session_ttl_minutes must be positive")

        if reopen_inactivity_minutes >= session_ttl_minutes:
            raise ValueError("reopen_inactivity_minutes must be less than session_ttl_minutes")

        self._session_factory = session_factory

        self._pak_test_catalog = PakTestCatalogService(session_factory)

        self._reopen_inactivity = timedelta(minutes=reopen_inactivity_minutes)
        self._session_ttl = timedelta(minutes=session_ttl_minutes)

    @staticmethod
    async def has_batch_history(session: AsyncSession, batch_id: UUID) -> bool:
        return await VerificationSessionService.has_batch_history(session, batch_id)

    async def get(self, session_id: UUID) -> VerificationSession | None:
        async with self._session_factory() as session:
            return await VerificationSessionService(
                session, reopen_inactivity=self._reopen_inactivity
            ).get(session_id)

    async def get_detail(
        self,
        session_id: UUID,
    ) -> (
        tuple[
            VerificationSession,
            list[VerificationStep],
        ]
        | None
    ):
        async with self._session_factory() as session:
            return await VerificationSessionService(
                session, reopen_inactivity=self._reopen_inactivity
            ).get_detail(session_id)

    async def list(
        self,
        *,
        q: str | None,
        pak_id: UUID | None,
        status: VerificationSessionStatus | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[VerificationSession], int]:
        async with self._session_factory() as session:
            return await VerificationSessionService(
                session, reopen_inactivity=self._reopen_inactivity
            ).list(
                q=q,
                pak_id=pak_id,
                status=status,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def open_session(
        self,
        *,
        pak: PakDevice,
        kg_dev_eui: str,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> VerificationSession:
        async with transaction(self._session_factory) as session:
            return await VerificationSessionService(
                session, reopen_inactivity=self._reopen_inactivity
            ).open_session(
                pak=pak,
                kg_dev_eui=kg_dev_eui,
                slot_no=slot_no,
                firmware_version=firmware_version,
                total_steps=total_steps,
            )

    async def complete_session(
        self,
        *,
        pak: PakDevice,
        session_id: UUID,
        status: VerificationSessionStatus,
    ) -> VerificationSession:
        async with transaction(self._session_factory) as session:
            return await VerificationSessionService(
                session, reopen_inactivity=self._reopen_inactivity
            ).complete_session(
                pak=pak,
                session_id=session_id,
                status=status,
            )

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
        async with transaction(self._session_factory) as session:
            return await VerificationStepService(
                session, catalog=self._pak_test_catalog
            ).start_step(
                pak=pak,
                session_id=session_id,
                step_no=step_no,
                test_name=test_name,
                test_label=test_label,
                error_group_code=error_group_code,
            )

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
        async with transaction(self._session_factory) as session:
            return await VerificationStepService(
                session, catalog=self._pak_test_catalog
            ).complete_step(
                pak=pak,
                session_id=session_id,
                step_no=step_no,
                status=status,
                measurement_value=measurement_value,
                measurement_min_value=measurement_min_value,
                measurement_max_value=measurement_max_value,
                measurement_unit=measurement_unit,
            )

    async def expire_stale_sessions(self, *, batch_size: int = 100) -> int:
        return await VerificationCleanupService(
            self._session_factory, session_ttl=self._session_ttl
        ).expire_stale_sessions(batch_size=batch_size)
