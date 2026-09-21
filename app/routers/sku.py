from fastapi import APIRouter, Query, Response

from app.dependencies import CurrentUserDep, SkuServiceDep
from app.schemas.common import Page
from app.schemas.sku import SkuCreate, SkuOut, SkuUpdate, SkuUsageOut

router = APIRouter(prefix="/skus", tags=["SKU"])


@router.get("", response_model=Page[SkuOut])
async def search_skus(
    service: SkuServiceDep,
    _: CurrentUserDep,
    q: str | None = Query(None, description="Trade reference, EAN or product name fragment"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Page[SkuOut]:
    return await service.search(q, page, limit)


@router.get("/by-ean/{ean}", response_model=SkuOut)
async def get_sku_by_ean(ean: str, service: SkuServiceDep, _: CurrentUserDep) -> SkuOut:
    return await service.get_by_ean(ean)


@router.get("/{sku_id}", response_model=SkuOut)
async def get_sku(sku_id: int, service: SkuServiceDep, _: CurrentUserDep) -> SkuOut:
    return await service.get_sku(sku_id)


@router.post("", response_model=SkuOut, status_code=201)
async def create_sku(data: SkuCreate, service: SkuServiceDep, _: CurrentUserDep) -> SkuOut:
    return await service.create_sku(data)


@router.patch("/{sku_id}", response_model=SkuOut)
async def update_sku(sku_id: int, data: SkuUpdate, service: SkuServiceDep, _: CurrentUserDep) -> SkuOut:
    return await service.update_sku(sku_id, data)


@router.get("/{sku_id}/usage", response_model=list[SkuUsageOut])
async def get_sku_usage(sku_id: int, service: SkuServiceDep, _: CurrentUserDep) -> list[SkuUsageOut]:
    return await service.usage(sku_id)


@router.delete("/{sku_id}", status_code=204)
async def delete_sku(sku_id: int, service: SkuServiceDep, _: CurrentUserDep) -> Response:
    """409 while any return still has a line with this SKU (see /usage for which ones)."""
    await service.delete_sku(sku_id)
    return Response(status_code=204)
