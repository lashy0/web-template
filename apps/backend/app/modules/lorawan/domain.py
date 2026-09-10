from enum import StrEnum


class ActivationType(StrEnum):
    OTAA = "otaa"
    ABP = "abp"


class LoRaWanVersion(StrEnum):
    V1_0 = "1.0"
    V1_1 = "1.1"
