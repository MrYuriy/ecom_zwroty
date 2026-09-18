from fastapi import FastAPI

from app.core.exc.handlers import register_exception_handlers
from app.routers import api_router


def create_app() -> FastAPI:
    application = FastAPI(title="ecom_zwroty", version="0.1.0")
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/health", include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
