from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.line_image import LineImage
from app.models.return_order import OrderLine, ReturnOrder
from app.models.sku import Sku
from app.repositories.base import BaseRepository

# Everything a return is serialized with, loaded up front (async sessions can't lazy-load).
_WITH_LINES = selectinload(ReturnOrder.lines).options(selectinload(OrderLine.sku), selectinload(OrderLine.images))


class ReturnOrderRepository(BaseRepository[ReturnOrder]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReturnOrder)

    async def get_with_lines(self, order_uuid: UUID) -> ReturnOrder | None:
        query = select(ReturnOrder).where(ReturnOrder.uuid == order_uuid).options(_WITH_LINES)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def search(
        self,
        page: int,
        limit: int,
        number: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[ReturnOrder], int]:
        conditions = []
        if number:
            pattern = f"%{number}%"
            conditions.append(ReturnOrder.bo_wms_number.ilike(pattern) | ReturnOrder.tempo_number.ilike(pattern))
        if date_from:
            conditions.append(ReturnOrder.return_date >= date_from)
        if date_to:
            conditions.append(ReturnOrder.return_date <= date_to)

        rows_query = (
            select(ReturnOrder)
            .where(*conditions)
            .options(_WITH_LINES)
            .order_by(ReturnOrder.return_date.desc(), ReturnOrder.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        total_query = select(func.count()).select_from(ReturnOrder).where(*conditions)

        rows = (await self.session.execute(rows_query)).scalars().all()
        total = (await self.session.execute(total_query)).scalar() or 0
        return list(rows), total


class OrderLineRepository(BaseRepository[OrderLine]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrderLine)


class LineImageRepository(BaseRepository[LineImage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LineImage)

    async def file_names_for_order(self, order_uuid: UUID) -> list[str]:
        query = (
            select(LineImage.file_name)
            .join(OrderLine, OrderLine.uuid == LineImage.order_line_uuid)
            .where(OrderLine.return_order_uuid == order_uuid)
        )
        return list((await self.session.execute(query)).scalars().all())

    async def file_names_for_line(self, line_uuid: UUID) -> list[str]:
        query = select(LineImage.file_name).where(LineImage.order_line_uuid == line_uuid)
        return list((await self.session.execute(query)).scalars().all())

    async def count_for_line(self, line_uuid: UUID) -> int:
        query = select(func.count()).select_from(LineImage).where(LineImage.order_line_uuid == line_uuid)
        return (await self.session.execute(query)).scalar() or 0

    # ---------- naming: images are named after (order's BO/WMS number, line's SKU reference) ----------

    def _keyed(self, *columns):
        return (
            select(*columns)
            .select_from(LineImage)
            .join(OrderLine, OrderLine.uuid == LineImage.order_line_uuid)
            .join(ReturnOrder, ReturnOrder.uuid == OrderLine.return_order_uuid)
            .join(Sku, Sku.id == OrderLine.sku_id)
        )

    async def for_key(self, bo_wms_number: str | None, trade_reference: str) -> list[LineImage]:
        order_matches = (
            ReturnOrder.bo_wms_number == bo_wms_number
            if bo_wms_number is not None
            else ReturnOrder.bo_wms_number.is_(None)
        )
        query = self._keyed(LineImage).where(order_matches, Sku.trade_reference == trade_reference)
        return list((await self.session.execute(query)).scalars().all())

    async def _keys(self, *conditions) -> set[tuple[str | None, str]]:
        query = self._keyed(ReturnOrder.bo_wms_number, Sku.trade_reference).where(*conditions).distinct()
        return {(bo, ref) for bo, ref in (await self.session.execute(query)).all()}

    async def keys_for_order(self, order_uuid: UUID) -> set[tuple[str | None, str]]:
        return await self._keys(ReturnOrder.uuid == order_uuid)

    async def keys_for_line(self, line_uuid: UUID) -> set[tuple[str | None, str]]:
        return await self._keys(OrderLine.uuid == line_uuid)

    async def keys_for_sku(self, sku_id: int) -> set[tuple[str | None, str]]:
        return await self._keys(Sku.id == sku_id)

    async def all_keys(self) -> set[tuple[str | None, str]]:
        return await self._keys()
