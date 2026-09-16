from collections.abc import Callable
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.domains.production.contracts import LatestVerificationProjectionPort

from .commands import (
    CreatePrefix,
    CreateVersion,
    DeletePrefix,
    DeleteVersion,
    SetPrefixArchived,
    SetVersionArchived,
    UpdatePrefix,
    UpdateVersion,
)
from .queries import KgQueries
from .repository import KgRepository


def get_projection_factory(request: Request) -> Callable[[], LatestVerificationProjectionPort]:
    return cast(
        Callable[[], LatestVerificationProjectionPort],
        request.app.state.latest_verification_projection_port_factory,
    )


ProjectionFactoryDep = Annotated[
    Callable[[], LatestVerificationProjectionPort], Depends(get_projection_factory)
]


def create_repository(
    session: AsyncSession,
    projection_factory: Callable[[], LatestVerificationProjectionPort] | None = None,
) -> KgRepository:
    return (
        KgRepository(session)
        if projection_factory is None
        else KgRepository(session, projection_factory())
    )


def create_queries(
    session: AsyncSession,
    projection_factory: Callable[[], LatestVerificationProjectionPort] | None = None,
) -> KgQueries:
    return KgQueries(create_repository(session, projection_factory))


def create_prefix_command(session: AsyncSession) -> CreatePrefix:
    return CreatePrefix(KgRepository(session), TransactionalAuditWriter.from_session(session))


def update_prefix_command(session: AsyncSession) -> UpdatePrefix:
    return UpdatePrefix(KgRepository(session), TransactionalAuditWriter.from_session(session))


def set_prefix_archived_command(session: AsyncSession) -> SetPrefixArchived:
    return SetPrefixArchived(KgRepository(session), TransactionalAuditWriter.from_session(session))


def delete_prefix_command(session: AsyncSession) -> DeletePrefix:
    return DeletePrefix(KgRepository(session), TransactionalAuditWriter.from_session(session))


def create_version_command(session: AsyncSession) -> CreateVersion:
    return CreateVersion(KgRepository(session), TransactionalAuditWriter.from_session(session))


def update_version_command(session: AsyncSession) -> UpdateVersion:
    return UpdateVersion(KgRepository(session), TransactionalAuditWriter.from_session(session))


def set_version_archived_command(session: AsyncSession) -> SetVersionArchived:
    return SetVersionArchived(KgRepository(session), TransactionalAuditWriter.from_session(session))


def delete_version_command(session: AsyncSession) -> DeleteVersion:
    return DeleteVersion(KgRepository(session), TransactionalAuditWriter.from_session(session))
