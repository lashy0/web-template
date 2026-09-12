from enum import StrEnum


class KgCurrentState(StrEnum):
    REGISTERED = "REGISTERED"
    ON_OTK = "ON_OTK"
    OTK_PASSED = "OTK_PASSED"
    OTK_FAILED = "OTK_FAILED"
    IN_REPAIR = "IN_REPAIR"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    SCRAPPED = "SCRAPPED"
