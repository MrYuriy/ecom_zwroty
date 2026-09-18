from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.dependencies import CurrentUserDep, ReturnOrderServiceDep
from app.schemas.common import Page
from app.schemas.return_order import (
    OrderLineCreate,
    OrderLineUpdate,
    ReturnOrderCreate,
    ReturnOrderOut,
    ReturnOrderUpdate,
)

router = APIRouter(prefix="/returns", tags=["Returns"])


@router.post("", response_model=ReturnOrderOut, status_code=201)
async def create_order(
    data: ReturnOrderCreate, service: ReturnOrderServiceDep, current_user: CurrentUserDep
) -> ReturnOrderOut:
    return await service.create_order(data, operator_id=current_user.id)


@router.get("", response_model=Page[ReturnOrderOut])
async def list_orders(
    service: ReturnOrderServiceDep,
    _: CurrentUserDep,
    number: str | None = Query(None, description="BO/WMS or Tempo number fragment"),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Page[ReturnOrderOut]:
    return await service.list_orders(page, limit, number=number, date_from=date_from, date_to=date_to)


@router.get("/{order_uuid}", response_model=ReturnOrderOut)
async def get_order(order_uuid: UUID, service: ReturnOrderServiceDep, _: CurrentUserDep) -> ReturnOrderOut:
    return await service.get_order(order_uuid)


@router.patch("/{order_uuid}", response_model=ReturnOrderOut)
async def update_order(
    order_uuid: UUID, data: ReturnOrderUpdate, service: ReturnOrderServiceDep, _: CurrentUserDep
) -> ReturnOrderOut:
    return await service.update_order(order_uuid, data)


@router.delete("/{order_uuid}", status_code=204)
async def delete_order(order_uuid: UUID, service: ReturnOrderServiceDep, _: CurrentUserDep) -> Response:
    await service.delete_order(order_uuid)
    return Response(status_code=204)


@router.post("/{order_uuid}/lines", response_model=ReturnOrderOut, status_code=201)
async def add_line(
    order_uuid: UUID, data: OrderLineCreate, service: ReturnOrderServiceDep, _: CurrentUserDep
) -> ReturnOrderOut:
    return await service.add_line(order_uuid, data)


@router.patch("/{order_uuid}/lines/{line_uuid}", response_model=ReturnOrderOut)
async def update_line(
    order_uuid: UUID,
    line_uuid: UUID,
    data: OrderLineUpdate,
    service: ReturnOrderServiceDep,
    _: CurrentUserDep,
) -> ReturnOrderOut:
    return await service.update_line(order_uuid, line_uuid, data)


@router.delete("/{order_uuid}/lines/{line_uuid}", response_model=ReturnOrderOut)
async def delete_line(
    order_uuid: UUID, line_uuid: UUID, service: ReturnOrderServiceDep, _: CurrentUserDep
) -> ReturnOrderOut:
    return await service.delete_line(order_uuid, line_uuid)
