from fastapi import APIRouter

from app.api.v1.endpoints.admin.security_admin import router as admin_security_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.order import router as order_router
from app.api.v1.endpoints.product import router as product_router
from app.api.v1.endpoints.protected import router as protected_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(protected_router)
api_router.include_router(product_router)
api_router.include_router(order_router)
api_router.include_router(admin_security_router)
