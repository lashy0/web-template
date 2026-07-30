import asyncio

from fastapi import APIRouter, Request, Response, status

from app.api.deps import DatabaseDep, RedisDep
from app.modules.health.schemas import ApplicationStatus, DependencyStatus, ReadinessResponse
from app.modules.health.service import is_postgres_ready, is_redis_ready

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/live")
async def liveness(
    request: Request,
) -> dict[str, str]:
    return {
        "status": "ok",
        "version": request.app.version,
    }


@router.get(
    "/ready",
    response_model=ReadinessResponse,
)
async def readiness(
    response: Response,
    database: DatabaseDep,
    redis: RedisDep,
) -> ReadinessResponse:
    postgres_ready, redis_ready = await asyncio.gather(
        is_postgres_ready(database.engine),
        is_redis_ready(redis),
    )

    checks_ready = {
        "postgres": postgres_ready,
        "redis": redis_ready,
    }

    application_ready = all(checks_ready.values())

    application_status: ApplicationStatus = "ready" if application_ready else "not_ready"

    dependency_statuses: dict[str, DependencyStatus] = {
        name: "up" if ready else "down" for name, ready in checks_ready.items()
    }

    if not application_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=application_status,
        checks=dependency_statuses,
    )
