"""Audit domain dependencies."""

from __future__ import annotations

from typing import Any

from litestar import Request
from litestar.di import NamedDependency
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.domain.audit.changes import ChangeRecorder
from app.domain.audit.services import AuditLogService
from app.lib.audit import Actor
from app.lib.deps import create_service_provider
from app.lib.realtime import Realtime
from app.lib.uow import UnitOfWork

provide_audit_log_service = create_service_provider(
    AuditLogService,
    load=[selectinload(m.AuditLog.actor)],
    error_messages={
        "duplicate_key": "Audit log entry already exists.",
        "integrity": "Audit log operation failed.",
    },
)


def actor_of_user(user: m.User) -> Actor:
    """Snapshot a user's audit identity."""
    return Actor(id=user.id, login=user.identity_login, name=user.name)


def actor_of_pak(pak: m.PakDevice) -> Actor:
    """Identify a PAK by its code, without a user ID."""
    return Actor(login=pak.code)


def provide_change_recorder(
    request: Request[m.User, Any, Any],
    audit_service: NamedDependency[AuditLogService],
    uow: NamedDependency[UnitOfWork],
    realtime: NamedDependency[Realtime],
) -> ChangeRecorder:
    """Return the recorder of the signed-in user's changes in this request."""
    return ChangeRecorder(request, audit_service, uow, realtime, actor_of_user(request.user))


def provide_machine_change_recorder(
    request: Request[Any, Any, Any],
    current_pak: NamedDependency[m.PakDevice],
    audit_service: NamedDependency[AuditLogService],
    uow: NamedDependency[UnitOfWork],
    realtime: NamedDependency[Realtime],
) -> ChangeRecorder:
    """Return the recorder with the authenticated PAK as its audit actor."""
    return ChangeRecorder(request, audit_service, uow, realtime, actor_of_pak(current_pak))


__all__ = (
    "actor_of_pak",
    "actor_of_user",
    "provide_audit_log_service",
    "provide_change_recorder",
    "provide_machine_change_recorder",
)
