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


class BatchStatus(StrEnum):
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"


class KgState(StrEnum):
    """Lifecycle of a KG unit; verification results are tracked separately.

    A unit starts ``registered``; packing makes it ``packed`` for good.
    """

    REGISTERED = "registered"
    PACKED = "packed"
    SCRAPPED = "scrapped"


class KgOtkStatus(StrEnum):
    """Outcome of the last completed verification of a KG unit on an OTK-line PAK."""

    NOT_VERIFIED = "not_verified"
    PASSED = "passed"
    FAILED = "failed"


class VerificationSessionStatus(StrEnum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"
    INCOMPLETE = "incomplete"
    """Closed by the system: the PAK stopped reporting or moved on."""


class VerificationStepStatus(StrEnum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"
