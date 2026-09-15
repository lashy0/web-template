"""Application roles shared by every bounded context."""

from enum import StrEnum


class Role(StrEnum):
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    ENGINEER = "engineer"
    PACKER = "packer"
    OPERATOR = "operator"


__all__ = ["Role"]
