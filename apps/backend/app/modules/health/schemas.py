from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DependencyStatus = Literal["up", "down"]
ApplicationStatus = Literal["ready", "not_ready"]


class LivenessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "version": "0.1.0",
                },
            ],
        },
    )

    status: Literal["ok"] = Field(
        description="Application process status.",
    )
    version: str = Field(
        description="Running backend version.",
    )


class ReadinessChecks(BaseModel):
    postgres: DependencyStatus = Field(
        description="PostgreSQL connection status.",
    )
    redis: DependencyStatus = Field(
        description="Redis connection status.",
    )
    kratos: DependencyStatus = Field(
        description="Ory Kratos Admin API status.",
    )


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ready",
                    "checks": {
                        "postgres": "up",
                        "redis": "up",
                        "kratos": "up",
                    },
                },
            ],
        },
    )

    status: ApplicationStatus = Field(
        description="Overall application readiness.",
    )
    checks: ReadinessChecks = Field(
        description="Readiness status of required dependencies.",
    )
