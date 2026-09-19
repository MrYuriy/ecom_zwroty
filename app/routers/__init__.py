from fastapi import APIRouter

from app.routers import auth, images, integration, returns, sku, users, wms_orders

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(sku.router)
api_router.include_router(returns.router)
api_router.include_router(images.router)
api_router.include_router(wms_orders.router)
api_router.include_router(integration.router)
