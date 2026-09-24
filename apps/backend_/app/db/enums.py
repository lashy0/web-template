from enum import Enum, StrEnum


def enum_values(enum: type[Enum]) -> list[str]:
    """Persist enum values rather than member names in SQLAlchemy ``Enum`` columns."""
    return [str(item.value) for item in enum]


class UserRole(StrEnum):
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    ENGINEER = "engineer"
    PACKER = "packer"
    OPERATOR = "operator"


class PakDeviceKind(StrEnum):
    ENGINEERING = "engineering"
    OTK_LINE = "otk_line"
