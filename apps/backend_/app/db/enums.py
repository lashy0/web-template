from enum import StrEnum


class UserRole(StrEnum):
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    ENGINEER = "engineer"
    PACKER = "packer"
    OPERATOR = "operator"
