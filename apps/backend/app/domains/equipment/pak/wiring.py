from collections.abc import Callable
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.infrastructure.hydra.pak import HydraPakOAuthClientAdapter

from .commands import (
    CreatePak,
    DeletePak,
    GetPakAccessKey,
    RotatePakAccessKey,
    SetPakActive,
    SetPakArchived,
    UpdatePak,
)
from .contracts import PakVerificationHistoryPort
from .queries import PakQueries


def get_oauth_client(request: Request) -> HydraPakOAuthClientAdapter:
    return HydraPakOAuthClientAdapter(request.app.state.hydra_client_manager)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_verification_history_factory(
    request: Request,
) -> Callable[[AsyncSession], PakVerificationHistoryPort]:
    return cast(
        Callable[[AsyncSession], PakVerificationHistoryPort],
        request.app.state.pak_verification_history_factory,
    )


OAuthClientDep = Annotated[HydraPakOAuthClientAdapter, Depends(get_oauth_client)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
VerificationHistoryFactoryDep = Annotated[
    Callable[[AsyncSession], PakVerificationHistoryPort], Depends(get_verification_history_factory)
]


def create_queries(session_factory: async_sessionmaker[AsyncSession]) -> PakQueries:
    return PakQueries(session_factory)


def create_pak_command(
    session_factory: async_sessionmaker[AsyncSession],
    oauth: HydraPakOAuthClientAdapter,
    settings: Settings,
) -> CreatePak:
    return CreatePak(session_factory, oauth, settings.PAK_ACCESS_KEY_ENCRYPTION_KEY)


def get_access_key_command(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings
) -> GetPakAccessKey:
    return GetPakAccessKey(session_factory, settings.PAK_ACCESS_KEY_ENCRYPTION_KEY)


def rotate_access_key_command(
    session_factory: async_sessionmaker[AsyncSession],
    oauth: HydraPakOAuthClientAdapter,
    settings: Settings,
) -> RotatePakAccessKey:
    return RotatePakAccessKey(session_factory, oauth, settings.PAK_ACCESS_KEY_ENCRYPTION_KEY)


def update_pak_command(session_factory: async_sessionmaker[AsyncSession]) -> UpdatePak:
    return UpdatePak(session_factory)


def set_active_command(session_factory: async_sessionmaker[AsyncSession]) -> SetPakActive:
    return SetPakActive(session_factory)


def set_archived_command(session_factory: async_sessionmaker[AsyncSession]) -> SetPakArchived:
    return SetPakArchived(session_factory)


def delete_pak_command(
    session_factory: async_sessionmaker[AsyncSession],
    oauth: HydraPakOAuthClientAdapter,
    verification_history: Callable[[AsyncSession], PakVerificationHistoryPort],
    settings: Settings,
) -> DeletePak:
    return DeletePak(
        session_factory, oauth, verification_history, settings.PAK_ACCESS_KEY_ENCRYPTION_KEY
    )
