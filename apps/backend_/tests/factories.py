"""Test data factories using Polyfactory."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from polyfactory import Use
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from uuid_utils.compat import uuid7

from app.db import models as m
from app.db.enums import UserRole


class UserFactory(SQLAlchemyFactory[m.User]):
    """Factory for User model."""

    __model__ = m.User
    __set_relationships__ = True

    id = Use(uuid7)
    identity_id = Use(uuid4)
    identity_login = Use(lambda: f"user-{uuid4().hex[:8]}")
    identity_active = True
    name = Use(lambda: f"Test User {uuid4().hex[:8]}")
    role = UserRole.OPERATOR
    archived_at = None
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))


class AdminUserFactory(UserFactory):
    """Factory for administrator users."""

    identity_login = Use(lambda: f"admin-{uuid4().hex[:8]}")
    name = Use(lambda: f"Admin User {uuid4().hex[:8]}")
    role = UserRole.ADMINISTRATOR


class ArchivedUserFactory(UserFactory):
    """Factory for archived users."""

    identity_active = False
    archived_at = Use(lambda: datetime.now(UTC))
