from fastapi import APIRouter

from .group import router as group_router
from .type import router as type_router

router = APIRouter(prefix="/defects", tags=["defects"])
router.include_router(group_router)
router.include_router(type_router)

__all__ = ["router"]
