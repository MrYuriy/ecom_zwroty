from fastapi import APIRouter

from app.routers import auth, images, integration, returns, sku, sku_imports, users, wms_orders

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(sku.router)
api_router.include_router(sku_imports.router)
api_router.include_router(returns.router)
api_router.include_router(images.router)
api_router.include_router(wms_orders.router)
api_router.include_router(integration.router)
