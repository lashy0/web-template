from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.kratos.users import KratosUserIdentityProvider

from .commands import (
    CreateUser,
    DeleteUser,
    SetUserActive,
    SetUserArchived,
    SetUserPassword,
    UpdateUser,
)
from .queries import UserQueries


def get_identity_provider(request: Request) -> KratosUserIdentityProvider:
    return KratosUserIdentityProvider(request.app.state.identity_manager)


IdentityProviderDep = Annotated[KratosUserIdentityProvider, Depends(get_identity_provider)]


def create_queries(session_factory: async_sessionmaker[AsyncSession]) -> UserQueries:
    return UserQueries(session_factory)


def create_user_command(
    session_factory: async_sessionmaker[AsyncSession], identities: KratosUserIdentityProvider
) -> CreateUser:
    return CreateUser(session_factory, identities)


def update_user_command(
    session_factory: async_sessionmaker[AsyncSession], identities: KratosUserIdentityProvider
) -> UpdateUser:
    return UpdateUser(session_factory, identities)


def set_password_command(
    session_factory: async_sessionmaker[AsyncSession], identities: KratosUserIdentityProvider
) -> SetUserPassword:
    return SetUserPassword(session_factory, identities)


def set_active_command(
    session_factory: async_sessionmaker[AsyncSession], identities: KratosUserIdentityProvider
) -> SetUserActive:
    return SetUserActive(session_factory, identities)


def set_archived_command(
    session_factory: async_sessionmaker[AsyncSession], identities: KratosUserIdentityProvider
) -> SetUserArchived:
    return SetUserArchived(session_factory, identities)


def delete_user_command(
    session_factory: async_sessionmaker[AsyncSession], identities: KratosUserIdentityProvider
) -> DeleteUser:
    return DeleteUser(session_factory, identities)
