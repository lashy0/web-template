"""Audit log service for tracking system events."""

from __future__ import annotations

from collections import defaultdict
from contextlib import suppress
from typing import TYPE_CHECKING, Any
from uuid import UUID

from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import select

from app.db import models as m
from app.lib.audit import AuditTarget, audit_target_fields, audit_target_models

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar import Request


class AuditLogService(service.SQLAlchemyAsyncRepositoryService[m.AuditLog]):
    """Service for audit log operations."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.AuditLog]):
        """AuditLog SQLAlchemy Repository."""

        model_type = m.AuditLog

    repository_type = Repo

    async def log_action(
        self,
        action: str,
        actor_id: UUID | None = None,
        actor_login: str | None = None,
        actor_name: str | None = None,
        target: AuditTarget | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request: Request[Any, Any, Any] | None = None,
    ) -> m.AuditLog:
        """Create a new audit log entry.

        Args:
            action: The action performed (e.g., 'user.created', 'login.failed')
            actor_id: ID of the user performing the action
            actor_login: Login of the actor
            actor_name: Name of the actor
            target: The record the action concerns; it names its type, id, label and name
            details: Additional context as JSON
            ip_address: Request IP address (extracted from request if not provided)
            user_agent: Request user agent (extracted from request if not provided)
            request: Optional Litestar request to extract ip_address and user_agent from

        Returns:
            Created AuditLog instance
        """

        if request is not None:
            if ip_address is None:
                ip_address = request.client.host if request.client else None

            if user_agent is None:
                user_agent = request.headers.get("user-agent")

        return await self.create(
            {
                "action": action,
                "actor_id": actor_id,
                "actor_login": actor_login,
                "actor_name": actor_name,
                **(audit_target_fields(target) if target is not None else {}),
                "details": details,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )

    async def current_target_labels(self, entries: Iterable[m.AuditLog]) -> dict[tuple[str, str], str]:
        """Return today's label of each target of ``entries``, keyed by target type and id.

        A target that has since been deleted has no label.
        """
        models = audit_target_models()
        ids_by_type: defaultdict[str, set[str]] = defaultdict(set)

        for entry in entries:
            model = models.get(entry.target_type or "")

            if model is not None and model.__audit_label__ is not None and entry.target_id:
                ids_by_type[model.__audit_type__].add(entry.target_id)

        labels: dict[tuple[str, str], str] = {}

        for target_type, ids in ids_by_type.items():
            model = models[target_type]
            id_column = getattr(model, model.__audit_id__)
            label_column = getattr(model, model.__audit_label__ or "")
            rows = await self.repository.session.execute(
                select(id_column, label_column).where(id_column.in_(_typed_ids(id_column, ids)))
            )
            labels.update(
                {(target_type, str(target_id)): str(label) for target_id, label in rows.tuples() if label is not None}
            )

        return labels


def _typed_ids(id_column: Any, ids: Iterable[str]) -> list[Any]:
    """``ids`` as values of ``id_column``; an id that is not a valid UUID matches no record and is left out."""
    if id_column.type.python_type is not UUID:
        return list(ids)

    typed: list[Any] = []

    for value in ids:
        with suppress(ValueError):
            typed.append(UUID(value))

    return typed
