from dataclasses import dataclass


@dataclass(slots=True)
class SystemVersion:
    version: str
