from fastapi import APIRouter

from app.routers import auth, sku, users

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(sku.router)
