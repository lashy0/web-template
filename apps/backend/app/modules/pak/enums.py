from enum import StrEnum


class PakDeviceKind(StrEnum):
    ENGINEERING = "engineering"
    OTK_LINE = "otk_line"


class PakStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
