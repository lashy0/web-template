from collections.abc import Callable
from datetime import timedelta
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.core.config import Settings

from .commands import (
    CompleteVerificationSession,
    CompleteVerificationStep,
    StartVerificationSession,
    StartVerificationStep,
)
from .contracts import VerificationKgPort, VerificationPakPort
from .queries import VerificationQueries
from .repository import VerificationRepository


def get_kg_port_factory(request: Request) -> Callable[[AsyncSession], VerificationKgPort]:
    return cast(
        Callable[[AsyncSession], VerificationKgPort], request.app.state.verification_kg_port_factory
    )


def get_pak_adapter(request: Request) -> Callable[[object], VerificationPakPort]:
    return cast(Callable[[object], VerificationPakPort], request.app.state.verification_pak_adapter)


def get_reopen_inactivity(request: Request) -> timedelta:
    settings: Settings = request.app.state.settings
    return timedelta(minutes=settings.VERIFICATION_SESSION_REOPEN_INACTIVITY_MINUTES)


KgPortFactoryDep = Annotated[
    Callable[[AsyncSession], VerificationKgPort], Depends(get_kg_port_factory)
]
PakAdapterDep = Annotated[Callable[[object], VerificationPakPort], Depends(get_pak_adapter)]
ReopenInactivityDep = Annotated[timedelta, Depends(get_reopen_inactivity)]


def create_queries(session: AsyncSession) -> VerificationQueries:
    return VerificationQueries(VerificationRepository(session))


def start_session_command(
    session: AsyncSession,
    kg_port_factory: Callable[[AsyncSession], VerificationKgPort],
    reopen_inactivity: timedelta,
) -> StartVerificationSession:
    return StartVerificationSession(
        VerificationRepository(session),
        kg_port_factory(session),
        reopen_inactivity=reopen_inactivity,
    )


def start_step_command(session: AsyncSession) -> StartVerificationStep:
    return StartVerificationStep(
        VerificationRepository(session), TransactionalAuditWriter.from_session(session)
    )


def complete_step_command(session: AsyncSession) -> CompleteVerificationStep:
    return CompleteVerificationStep(VerificationRepository(session))


def complete_session_command(session: AsyncSession) -> CompleteVerificationSession:
    return CompleteVerificationSession(VerificationRepository(session))
