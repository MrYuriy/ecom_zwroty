from datetime import date
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import ObjectNotFoundException
from app.database.postgres import get_session
from app.models.return_order import OrderLine, ReturnOrder
from app.repositories.return_order import OrderLineRepository, ReturnOrderRepository
from app.repositories.sku import SkuRepository
from app.schemas.common import Page
from app.schemas.return_order import (
    OrderLineCreate,
    OrderLineUpdate,
    ReturnOrderCreate,
    ReturnOrderOut,
    ReturnOrderUpdate,
)

_CLEARABLE_LINE_FIELDS = {"damage_description", "remarks"}


class ReturnOrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.orders = ReturnOrderRepository(session)
        self.lines = OrderLineRepository(session)
        self.skus = SkuRepository(session)

    async def _get_order(self, order_uuid: UUID) -> ReturnOrder:
        order = await self.orders.get_one(uuid=order_uuid)
        if not order:
            raise ObjectNotFoundException(order_uuid, "Return order")
        return order

    async def _get_line(self, order_uuid: UUID, line_uuid: UUID) -> OrderLine:
        line = await self.lines.get_one(uuid=line_uuid, return_order_uuid=order_uuid)
        if not line:
            raise ObjectNotFoundException(line_uuid, "Order line")
        return line

    async def _ensure_sku_exists(self, sku_id: int) -> None:
        if not await self.skus.get_one(id=sku_id):
            raise ObjectNotFoundException(sku_id, "SKU")

    async def _reload(self, order_uuid: UUID) -> ReturnOrderOut:
        # Relationships expire after commit; reload eagerly before serializing (avoids MissingGreenlet).
        order = await self.orders.get_with_lines(order_uuid)
        if not order:
            raise ObjectNotFoundException(order_uuid, "Return order")
        return ReturnOrderOut.model_validate(order)

    async def create_order(self, data: ReturnOrderCreate, operator_id: int) -> ReturnOrderOut:
        payload = data.model_dump(exclude_none=True)
        payload["operator_id"] = operator_id
        order = await self.orders.create_one(payload)
        return await self._reload(order.uuid)

    async def get_order(self, order_uuid: UUID) -> ReturnOrderOut:
        return await self._reload(order_uuid)

    async def list_orders(
        self,
        page: int,
        limit: int,
        number: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> Page[ReturnOrderOut]:
        orders, total = await self.orders.search(page, limit, number=number, date_from=date_from, date_to=date_to)
        return Page(items=[ReturnOrderOut.model_validate(o) for o in orders], total=total, page=page, limit=limit)

    async def update_order(self, order_uuid: UUID, data: ReturnOrderUpdate) -> ReturnOrderOut:
        order = await self._get_order(order_uuid)
        changes = data.model_dump(exclude_unset=True)
        # return_date is required; an explicit null means "leave it as is".
        if changes.get("return_date") is None:
            changes.pop("return_date", None)
        await self.orders.update_one(order, changes)
        return await self._reload(order_uuid)

    async def delete_order(self, order_uuid: UUID) -> None:
        await self.orders.delete_one(await self._get_order(order_uuid))

    async def add_line(self, order_uuid: UUID, data: OrderLineCreate) -> ReturnOrderOut:
        await self._get_order(order_uuid)
        await self._ensure_sku_exists(data.sku_id)
        await self.lines.create_one({**data.model_dump(), "return_order_uuid": order_uuid})
        return await self._reload(order_uuid)

    async def update_line(self, order_uuid: UUID, line_uuid: UUID, data: OrderLineUpdate) -> ReturnOrderOut:
        line = await self._get_line(order_uuid, line_uuid)
        # Only the free-text fields may be cleared; a null on a required field is ignored.
        changes = {
            key: value
            for key, value in data.model_dump(exclude_unset=True).items()
            if value is not None or key in _CLEARABLE_LINE_FIELDS
        }
        if "sku_id" in changes:
            await self._ensure_sku_exists(changes["sku_id"])
        await self.lines.update_one(line, changes)
        return await self._reload(order_uuid)

    async def delete_line(self, order_uuid: UUID, line_uuid: UUID) -> ReturnOrderOut:
        await self.lines.delete_one(await self._get_line(order_uuid, line_uuid))
        return await self._reload(order_uuid)


def get_return_order_service(session: AsyncSession = Depends(get_session)) -> ReturnOrderService:
    return ReturnOrderService(session)
