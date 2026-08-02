import asyncio

from fastapi import APIRouter, Request, Response, status

from app.api.deps import DatabaseDep, RedisDep
from app.core.config import Settings
from app.modules.health.schemas import (
    ApplicationStatus,
    LivenessResponse,
    ReadinessChecks,
    ReadinessResponse,
)
from app.modules.health.service import is_postgres_ready, is_redis_ready

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Check application liveness",
    description=("Returns `200 OK` while the backend process is running. "),
    response_description="The application process is alive.",
)
async def liveness(
    request: Request,
) -> LivenessResponse:
    return LivenessResponse(
        status="ok",
        version=request.app.version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Check application readiness",
    description=(
        "Checks whether the backend can serve requests. PostgreSQL and Redis "
        "are checked concurrently. Returns `503 Service Unavailable` when at "
        "least one required dependency is unavailable."
    ),
    response_description="Current readiness state and dependency checks.",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "At least one required dependency is unavailable.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "not_ready",
                        "checks": {
                            "postgres": "up",
                            "redis": "down",
                        },
                    },
                },
            },
        },
    },
)
async def readiness(
    request: Request,
    response: Response,
    database: DatabaseDep,
    redis: RedisDep,
) -> ReadinessResponse:
    settings: Settings = request.app.state.settings

    postgres_ready, redis_ready = await asyncio.gather(
        is_postgres_ready(database.engine, timeout=settings.READINESS_TIMEOUT),
        is_redis_ready(redis, timeout=settings.READINESS_TIMEOUT),
    )

    checks_ready = {
        "postgres": postgres_ready,
        "redis": redis_ready,
    }

    application_ready = all(checks_ready.values())

    application_status: ApplicationStatus = "ready" if application_ready else "not_ready"

    dependency_statuses = ReadinessChecks(
        postgres="up" if postgres_ready else "down",
        redis="up" if redis_ready else "down",
    )

    if not application_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=application_status,
        checks=dependency_statuses,
    )
