from fastapi import APIRouter

from app.routers import (
    auth,
    images,
    integration,
    reports,
    returns,
    sku,
    sku_imports,
    users,
    wms_orders,
    work_logs,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(sku.router)
api_router.include_router(sku_imports.router)
api_router.include_router(returns.router)
api_router.include_router(images.router)
api_router.include_router(reports.router)
api_router.include_router(wms_orders.router)
api_router.include_router(work_logs.router)
api_router.include_router(integration.router)
