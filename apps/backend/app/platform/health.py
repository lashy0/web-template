import asyncio
from asyncio.exceptions import TimeoutError
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.deps import DatabaseDep, RedisDep
from app.core.config import Settings

DependencyStatus = Literal["up", "down"]
ApplicationStatus = Literal["ready", "not_ready"]


class LivenessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"status": "ok", "version": "0.1.0"}]}
    )
    status: Literal["ok"] = Field(description="Application process status.")
    version: str = Field(description="Running backend version.")


class ReadinessChecks(BaseModel):
    postgres: DependencyStatus = Field(description="PostgreSQL connection status.")
    redis: DependencyStatus = Field(description="Redis connection status.")
    kratos: DependencyStatus = Field(description="Ory Kratos Admin API status.")


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"status": "ready", "checks": {"postgres": "up", "redis": "up", "kratos": "up"}}
            ]
        }
    )
    status: ApplicationStatus = Field(description="Overall application readiness.")
    checks: ReadinessChecks = Field(description="Readiness status of required dependencies.")


async def is_postgres_ready(engine: AsyncEngine, *, timeout: float) -> bool:
    try:
        async with asyncio.timeout(timeout):
            async with engine.begin() as conn:
                await conn.execute(select(1))
        return True
    except (TimeoutError, SQLAlchemyError):
        return False


async def is_redis_ready(client: Redis, *, timeout: float) -> bool:
    try:
        async with asyncio.timeout(timeout):
            return bool(await client.ping())
    except (TimeoutError, RedisError):
        return False


router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Check application liveness",
    description="Returns `200 OK` while the backend process is running. ",
    response_description="The application process is alive.",
)
async def liveness(request: Request) -> LivenessResponse:
    return LivenessResponse(status="ok", version=request.app.version)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Check application readiness",
    description="Checks whether the backend can serve requests. PostgreSQL and Redis are checked concurrently. Returns `503 Service Unavailable` when at least one required dependency is unavailable.",
    response_description="Current readiness state and dependency checks.",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "At least one required dependency is unavailable.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "not_ready",
                        "checks": {"postgres": "up", "redis": "down"},
                    }
                }
            },
        }
    },
)
async def readiness(
    request: Request, response: Response, database: DatabaseDep, redis: RedisDep
) -> ReadinessResponse:
    settings: Settings = request.app.state.settings
    postgres_ready, redis_ready, kratos_ready = await asyncio.gather(
        is_postgres_ready(database.engine, timeout=settings.READINESS_TIMEOUT),
        is_redis_ready(redis, timeout=settings.READINESS_TIMEOUT),
        request.app.state.identity_manager.is_ready(),
    )
    checks_ready = {"postgres": postgres_ready, "redis": redis_ready, "kratos": kratos_ready}
    application_ready = all(checks_ready.values())
    if not application_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if application_ready else "not_ready",
        checks=ReadinessChecks(
            **{key: "up" if value else "down" for key, value in checks_ready.items()}
        ),
    )
