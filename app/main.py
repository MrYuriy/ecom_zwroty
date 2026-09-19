import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.cabinet import register_cabinet
from app.core import settings
from app.core.exc.handlers import register_exception_handlers
from app.routers import api_router
from app.tasks.wms_sync import run_periodic_sync

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
# One line per Google request is noise; the sync logs its own summary.
logging.getLogger("httpx").setLevel(logging.WARNING)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    sync_task = asyncio.create_task(run_periodic_sync()) if settings.google.WMS_SYNC_ENABLED else None
    try:
        yield
    finally:
        if sync_task:
            sync_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sync_task


def create_app() -> FastAPI:
    application = FastAPI(title="ecom_zwroty", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/health", include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok"}

    # Same origin as the API, so the cabinet needs no CORS.
    register_cabinet(application)
    return application


app = create_app()
