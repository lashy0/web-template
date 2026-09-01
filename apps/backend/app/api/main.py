from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.pak.router import router as pak_router
from app.modules.users.router import router as users_router
from app.modules.kg.router import router as kg_router
from app.modules.batch.router import router as batch_router
from app.modules.verification.router import router as verification_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(users_router)
api_router.include_router(pak_router)
api_router.include_router(kg_router)
api_router.include_router(batch_router)
api_router.include_router(verification_router)
