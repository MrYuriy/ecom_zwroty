from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.dependencies import AdminUserDep, SkuImportServiceDep
from app.schemas.sku_import import SkuImportOut
from app.services.sku_import import get_session_factory, run_import

router = APIRouter(prefix="/sku-imports", tags=["SKU import"])


@router.post("", response_model=SkuImportOut, status_code=202)
async def start_import(
    background: BackgroundTasks,
    service: SkuImportServiceDep,
    admin: AdminUserDep,
    file: UploadFile = File(...),
    session_factory: async_sessionmaker = Depends(get_session_factory),
) -> SkuImportOut:
    """Upload the SKU/EAN export; it is processed in the background — poll /sku-imports/latest."""
    job, path = await service.start(file, admin.id)
    background.add_task(run_import, job.uuid, path, session_factory)
    return job


@router.get("/latest", response_model=SkuImportOut | None)
async def latest_import(service: SkuImportServiceDep, _: AdminUserDep) -> SkuImportOut | None:
    return await service.latest()


@router.get("/{import_uuid}", response_model=SkuImportOut)
async def get_import(import_uuid: UUID, service: SkuImportServiceDep, _: AdminUserDep) -> SkuImportOut:
    return await service.get(import_uuid)
