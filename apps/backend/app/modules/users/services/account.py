"""Retired compatibility module. Workflows moved to identity.users commands."""

from app.contexts.identity.users.commands.update import SetUserActive, SetUserPassword, UpdateUser

__all__ = ["SetUserActive", "SetUserPassword", "UpdateUser"]
