import builtins
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import IdentityManager
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role

from ..models import User
from .account import UserAccountService
from .bootstrap import BOOTSTRAP_ADMIN_USER_ID as BOOTSTRAP_ADMIN_USER_ID
from .bootstrap import UserBootstrapService
from .provisioning import UserProvisioningService
from .reconciliation import ReconciliationResult, UserReconciliationService


class UserManagementService:
    """Public compatibility gateway for the domain services."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: IdentityManager,
    ) -> None:
        self._account = UserAccountService(session_factory, identities)
        self._provisioning = UserProvisioningService(session_factory, identities)
        self._bootstrap = UserBootstrapService(session_factory, identities)
        self._reconciliation = UserReconciliationService(session_factory, identities)

    async def get(self, user_id: UUID) -> User | None:
        return await self._account.get(user_id)

    async def list(
        self,
        *,
        q: str | None,
        role: Role | None,
        auth_state: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[builtins.list[User], int]:
        return await self._account.list(
            q=q,
            role=role,
            auth_state=auth_state,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        login: str | None,
        name: str | None,
        role: Role | None,
    ) -> User:
        return await self._account.update(
            actor=actor,
            user_id=user_id,
            login=login,
            name=name,
            role=role,
        )

    async def set_password(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        password: str,
    ) -> None:
        return await self._account.set_password(
            actor=actor,
            user_id=user_id,
            password=password,
        )

    async def set_active(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        active: bool,
    ) -> User:
        return await self._account.set_active(
            actor=actor,
            user_id=user_id,
            active=active,
        )

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        archived: bool,
    ) -> User:
        return await self._account.set_archived(
            actor=actor,
            user_id=user_id,
            archived=archived,
        )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
    ) -> None:
        return await self._account.delete(
            actor=actor,
            user_id=user_id,
        )

    async def create(
        self,
        *,
        actor: CurrentPrincipal | None,
        name: str,
        role: Role,
        login: str,
        password: str,
        active: bool,
    ) -> User:
        return await self._provisioning.create(
            actor=actor,
            name=name,
            role=role,
            login=login,
            password=password,
            active=active,
        )

    async def bootstrap_first_administrator(
        self,
        *,
        name: str,
        login: str,
        password_loader: Callable[[], str | None],
    ) -> User | None:
        return await self._bootstrap.bootstrap_first_administrator(
            name=name, login=login, password_loader=password_loader
        )

    async def reconcile(self) -> ReconciliationResult:
        return await self._reconciliation.reconcile()
