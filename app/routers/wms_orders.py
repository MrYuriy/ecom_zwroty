from fastapi import APIRouter, Query

from app.dependencies import AdminUserDep, CurrentUserDep, WmsOrderServiceDep
from app.schemas.common import Page
from app.schemas.wms_order import WmsOrderOut, WmsSyncResult

router = APIRouter(prefix="/wms-orders", tags=["WMS orders"])


@router.get("", response_model=Page[WmsOrderOut])
async def list_wms_orders(
    service: WmsOrderServiceDep,
    _: AdminUserDep,
    q: str | None = Query(None, description="BO/WMS or Tempo number fragment"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Page[WmsOrderOut]:
    return await service.search(q, page, limit)


@router.get("/{bo_wms_number}", response_model=WmsOrderOut)
async def get_wms_order(bo_wms_number: str, service: WmsOrderServiceDep, _: CurrentUserDep) -> WmsOrderOut:
    return await service.get(bo_wms_number)


@router.post("/sync", response_model=WmsSyncResult)
async def sync_wms_orders(service: WmsOrderServiceDep, _: AdminUserDep) -> WmsSyncResult:
    return await service.sync_from_sheet()
