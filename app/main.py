from fastapi import FastAPI

from app.cabinet import register_cabinet
from app.core.exc.handlers import register_exception_handlers
from app.routers import api_router


def create_app() -> FastAPI:
    application = FastAPI(title="ecom_zwroty", version="0.1.0")
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/health", include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok"}

    # Same origin as the API, so the cabinet needs no CORS.
    register_cabinet(application)
    return application


app = create_app()
