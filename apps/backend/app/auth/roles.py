from enum import StrEnum


class Role(StrEnum):
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    ENGINEER = "engineer"
    PACKER = "packer"
    OPERATOR = "operator"
