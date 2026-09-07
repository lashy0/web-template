from fastapi import APIRouter

from .batch import router as batch_router
from .receipt import router as receipt_router
from .shipment import router as shipment_router

router = APIRouter()
router.include_router(batch_router)
router.include_router(receipt_router)
router.include_router(shipment_router)

__all__ = ["router"]
