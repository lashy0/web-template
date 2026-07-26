from typing import Literal

from pydantic import BaseModel

DependencyStatus = Literal["up", "down"]
ApplicationStatus = Literal["ready", "not_ready"]

class ReadinessResponse(BaseModel):
    status: ApplicationStatus
    checks: dict[str, DependencyStatus]
