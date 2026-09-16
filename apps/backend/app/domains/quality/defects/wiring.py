from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter

from .commands import (
    CreateDefectGroup,
    CreateDefectType,
    DeleteDefectGroup,
    DeleteDefectType,
    SetDefectGroupArchived,
    SetDefectTypeArchived,
    UpdateDefectGroup,
    UpdateDefectType,
)
from .queries import DefectQueries
from .repository import DefectGroupRepository, DefectTypeRepository


def create_queries(session: AsyncSession) -> DefectQueries:
    return DefectQueries(DefectGroupRepository(session), DefectTypeRepository(session))


def create_group_command(session: AsyncSession) -> CreateDefectGroup:
    return CreateDefectGroup(
        DefectGroupRepository(session), TransactionalAuditWriter.from_session(session)
    )


def update_group_command(session: AsyncSession) -> UpdateDefectGroup:
    return UpdateDefectGroup(
        DefectGroupRepository(session), TransactionalAuditWriter.from_session(session)
    )


def set_group_archived_command(session: AsyncSession) -> SetDefectGroupArchived:
    return SetDefectGroupArchived(
        DefectGroupRepository(session),
        DefectTypeRepository(session),
        TransactionalAuditWriter.from_session(session),
    )


def delete_group_command(session: AsyncSession) -> DeleteDefectGroup:
    return DeleteDefectGroup(
        DefectGroupRepository(session),
        DefectTypeRepository(session),
        TransactionalAuditWriter.from_session(session),
    )


def create_type_command(session: AsyncSession) -> CreateDefectType:
    return CreateDefectType(
        DefectGroupRepository(session),
        DefectTypeRepository(session),
        TransactionalAuditWriter.from_session(session),
    )


def update_type_command(session: AsyncSession) -> UpdateDefectType:
    return UpdateDefectType(
        DefectTypeRepository(session), TransactionalAuditWriter.from_session(session)
    )


def set_type_archived_command(session: AsyncSession) -> SetDefectTypeArchived:
    return SetDefectTypeArchived(
        DefectGroupRepository(session),
        DefectTypeRepository(session),
        TransactionalAuditWriter.from_session(session),
    )


def delete_type_command(session: AsyncSession) -> DeleteDefectType:
    return DeleteDefectType(
        DefectTypeRepository(session), TransactionalAuditWriter.from_session(session)
    )
