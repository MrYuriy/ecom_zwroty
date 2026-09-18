from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.return_order import OrderLine, ReturnOrder
from app.repositories.base import BaseRepository


class ReturnOrderRepository(BaseRepository[ReturnOrder]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReturnOrder)

    async def get_with_lines(self, order_uuid: UUID) -> ReturnOrder | None:
        query = (
            select(ReturnOrder)
            .where(ReturnOrder.uuid == order_uuid)
            .options(selectinload(ReturnOrder.lines).selectinload(OrderLine.sku))
        )
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
            .options(selectinload(ReturnOrder.lines).selectinload(OrderLine.sku))
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
