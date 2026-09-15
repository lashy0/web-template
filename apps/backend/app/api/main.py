from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.contexts.equipment.pak.router import router as pak_router
from app.contexts.identity.users.router import router as users_router
from app.contexts.production.batches.router import router as batches_router
from app.contexts.production.kg.router import router as kg_router
from app.contexts.production.production_orders.router import router as production_order_router
from app.contexts.production.receipts.router import router as receipts_router
from app.contexts.production.shipments.router import router as shipments_router
from app.contexts.quality.defects.router import router as defects_router
from app.contexts.quality.verification.router import (
    machine_router as machine_verification_router,
)
from app.contexts.quality.verification.router import (
    router as verification_router,
)
from app.modules.audit.router import router as audit_router
from app.platform.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(users_router)
api_router.include_router(pak_router)
api_router.include_router(kg_router)
api_router.include_router(batches_router)
api_router.include_router(receipts_router)
api_router.include_router(shipments_router)
api_router.include_router(production_order_router)
api_router.include_router(verification_router)
api_router.include_router(machine_verification_router)
api_router.include_router(defects_router)
