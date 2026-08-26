from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import Role
from app.modules.users.repository import UserRepository


@pytest.mark.integration
async def test_created_user_is_retrievable_by_both_identifiers(
    db_session: AsyncSession,
) -> None:
    identity_id = uuid4()
    repository = UserRepository(db_session)

    created = await repository.create(
        identity_id=identity_id,
        name="Alice Smith",
        role=Role.ENGINEER,
    )

    by_id = await repository.get_by_id(created.id)
    by_identity_id = await repository.get_by_identity_id(identity_id)

    assert by_id is not None
    assert by_id.id == created.id
    assert by_id.identity_id == identity_id
    assert by_id.name == "Alice Smith"
    assert by_id.role is Role.ENGINEER
    assert by_id.created_at.tzinfo is not None
    assert by_id.updated_at.tzinfo is not None
    assert by_identity_id is not None
    assert by_identity_id.id == created.id


@pytest.mark.integration
async def test_user_name_can_be_updated(db_session: AsyncSession) -> None:
    repository = UserRepository(db_session)
    user = await repository.create(
        identity_id=uuid4(),
        name="Old Name",
        role=Role.MANAGER,
    )

    updated = await repository.update_name(user, name="New Name")
    retrieved = await repository.get_by_id(user.id)

    assert updated.name == "New Name"
    assert retrieved is not None
    assert retrieved.name == "New Name"


@pytest.mark.integration
async def test_user_role_can_be_updated(db_session: AsyncSession) -> None:
    repository = UserRepository(db_session)
    identity_id = uuid4()
    user = await repository.create(
        identity_id=identity_id,
        name="Bob Brown",
        role=Role.OPERATOR,
    )

    updated = await repository.update_role(user, role=Role.ADMINISTRATOR)
    retrieved = await repository.get_by_identity_id(identity_id)

    assert updated.role is Role.ADMINISTRATOR
    assert retrieved is not None
    assert retrieved.role is Role.ADMINISTRATOR
