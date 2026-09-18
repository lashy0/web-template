"""Account domain guards and authentication."""

from __future__ import annotations

from typing import Any

from litestar.connection import ASGIConnection
from litestar.exceptions import PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler

from app.db import models as m
from app.db.enums import UserRole


def requires_administrator(
    connection: ASGIConnection[Any, m.User, Any, Any],
    _: BaseRouteHandler,
) -> None:
    if connection.user.role != UserRole.ADMINISTRATOR:
        raise PermissionDeniedException(
            detail="Administrator access required.",
        )
