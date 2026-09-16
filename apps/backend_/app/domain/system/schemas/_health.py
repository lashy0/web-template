from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class SystemHealth:
    app: str
    database_status: Literal["online", "offline"]
