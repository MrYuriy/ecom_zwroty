from fastapi import APIRouter

from app.routers import auth, images, returns, sku, users

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(sku.router)
api_router.include_router(returns.router)
api_router.include_router(images.router)
