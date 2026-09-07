from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.auth.contracts import Identity
from app.auth.exceptions import ForbiddenError
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.users.models import User
from app.modules.users.services import BOOTSTRAP_ADMIN_USER_ID, UserManagementService

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("operation", ["deactivate", "archive", "delete", "demote"])
async def test_ordinary_administrator_can_lose_access_while_root_is_preserved(
    database_session_factory, operation
):
    factory = database_session_factory
    root = User(
        id=BOOTSTRAP_ADMIN_USER_ID,
        identity_id=uuid4(),
        name="System administrator",
        role=Role.ADMINISTRATOR,
        identity_login="root",
        auth_state="active",
    )
    ordinary = User(
        id=uuid4(),
        identity_id=uuid4(),
        name="Administrator",
        role=Role.ADMINISTRATOR,
        identity_login="admin",
        auth_state="active",
    )
    async with factory() as session, session.begin():
        session.add_all([root, ordinary])
    identities = AsyncMock()
    identities.set_active.return_value = Identity(
        id=ordinary.identity_id, login=ordinary.identity_login, active=False
    )
    service = UserManagementService(factory, identities)
    actor = CurrentPrincipal(
        user_id=root.id, identity_id=root.identity_id, session_id=uuid4(), role=Role.ADMINISTRATOR
    )

    async def change(user_id):
        if operation == "deactivate":
            return await service.set_active(actor=actor, user_id=user_id, active=False)
        if operation == "archive":
            return await service.set_archived(actor=actor, user_id=user_id, archived=True)
        if operation == "delete":
            return await service.delete(actor=actor, user_id=user_id)
        return await service.update(
            actor=actor, user_id=user_id, login=None, name=None, role=Role.MANAGER
        )

    try:
        await change(ordinary.id)
        identities.reset_mock()
        with pytest.raises(ForbiddenError, match="system administrator"):
            await change(root.id)
        assert identities.mock_calls == []
        async with factory() as session:
            saved_root = await session.get(User, root.id)
            assert saved_root.role == Role.ADMINISTRATOR
            assert saved_root.auth_state == "active"
            assert saved_root.archived_at is None
            saved_user = await session.get(User, ordinary.id)
            if operation == "delete":
                assert saved_user is None
            elif operation == "demote":
                assert saved_user.role == Role.MANAGER
            else:
                assert saved_user.auth_state == "inactive"
                assert (saved_user.archived_at is not None) == (operation == "archive")
    finally:
        async with factory() as session, session.begin():
            await session.execute(delete(User).where(User.id.in_([root.id, ordinary.id])))


async def test_forbidden_role_change_does_not_change_provider_login(database_session_factory):
    factory = database_session_factory
    user = User(
        id=uuid4(),
        identity_id=uuid4(),
        name="Admin",
        role=Role.ADMINISTRATOR,
        identity_login="admin",
        auth_state="active",
    )
    async with factory() as session, session.begin():
        session.add(user)
    identities = AsyncMock()
    service = UserManagementService(factory, identities)
    actor = CurrentPrincipal(
        user_id=user.id, identity_id=user.identity_id, session_id=uuid4(), role=Role.ADMINISTRATOR
    )
    with pytest.raises(ForbiddenError):
        await service.update(
            actor=actor, user_id=user.id, login="changed", name=None, role=Role.MANAGER
        )
    identities.update_login.assert_not_called()
    async with factory() as session, session.begin():
        await session.execute(delete(User).where(User.id == user.id))
