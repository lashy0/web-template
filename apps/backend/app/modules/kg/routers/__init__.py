from fastapi import APIRouter

from .prefix import router as prefix_router
from .unit import router as unit_router
from .version import router as version_router

router = APIRouter()
router.include_router(prefix_router, prefix="/kg", tags=["kg"])
router.include_router(version_router, prefix="/kg", tags=["kg"])
router.include_router(unit_router, prefix="/kg", tags=["kg"])

__all__ = ["router"]
