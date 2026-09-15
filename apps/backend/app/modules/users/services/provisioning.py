"""Retired compatibility module. Workflow moved to identity.users.commands.create."""

from app.contexts.identity.users.commands.create import CreateUser

__all__ = ["CreateUser"]
