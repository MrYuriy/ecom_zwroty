from fastapi import APIRouter

from app.dependencies import AdminUserDep, CurrentUserDep, WmsOrderServiceDep
from app.schemas.wms_order import WmsOrderOut, WmsSyncResult

router = APIRouter(prefix="/wms-orders", tags=["WMS orders"])


@router.get("/{bo_wms_number}", response_model=WmsOrderOut)
async def get_wms_order(bo_wms_number: str, service: WmsOrderServiceDep, _: CurrentUserDep) -> WmsOrderOut:
    return await service.get(bo_wms_number)


@router.post("/sync", response_model=WmsSyncResult)
async def sync_wms_orders(service: WmsOrderServiceDep, _: AdminUserDep) -> WmsSyncResult:
    return await service.sync_from_sheet()
