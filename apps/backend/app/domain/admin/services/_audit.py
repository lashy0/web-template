"""Audit log service for tracking system events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m

if TYPE_CHECKING:
    from uuid import UUID

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
        target_type: str | None = None,
        target_id: str | None = None,
        target_label: str | None = None,
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
            target_type: Type of target entity (e.g., 'user', 'team')
            target_id: ID of target entity
            target_label: Human-readable label for target
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
                "target_type": target_type,
                "target_id": target_id,
                "target_label": target_label,
                "details": details,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )
