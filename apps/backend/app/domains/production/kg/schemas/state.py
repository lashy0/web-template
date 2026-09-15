from enum import StrEnum


class KgCurrentState(StrEnum):
    """Public compatibility enum; PACKED/SHIPPED are no longer projected."""

    REGISTERED = "REGISTERED"
    ON_OTK = "ON_OTK"
    OTK_PASSED = "OTK_PASSED"
    OTK_FAILED = "OTK_FAILED"
    OTK_ABORTED = "OTK_ABORTED"
    OTK_INCOMPLETE = "OTK_INCOMPLETE"
    IN_REPAIR = "IN_REPAIR"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    SCRAPPED = "SCRAPPED"
