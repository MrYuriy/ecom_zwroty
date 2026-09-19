from sqlalchemy import func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wms_order import WmsOrder
from app.repositories.base import BaseRepository

_INSERT_BATCH = 1000


class WmsOrderRepository(BaseRepository[WmsOrder]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WmsOrder)

    async def existing_numbers(self) -> set[str]:
        return set((await self.session.execute(select(WmsOrder.bo_wms_number))).scalars().all())

    async def insert_many(self, rows: list[dict]) -> None:
        for start in range(0, len(rows), _INSERT_BATCH):
            await self.session.execute(insert(WmsOrder), rows[start : start + _INSERT_BATCH])
        await self.session.commit()

    async def search(self, query: str | None, page: int, limit: int) -> tuple[list[WmsOrder], int]:
        condition = None
        if query:
            pattern = f"%{query}%"
            condition = or_(WmsOrder.bo_wms_number.ilike(pattern), WmsOrder.tempo_number.ilike(pattern))
        rows_query = (
            select(WmsOrder)
            .order_by(WmsOrder.created_at.desc(), WmsOrder.bo_wms_number.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        total_query = select(func.count()).select_from(WmsOrder)
        if condition is not None:
            rows_query = rows_query.where(condition)
            total_query = total_query.where(condition)
        rows = (await self.session.execute(rows_query)).scalars().all()
        total = (await self.session.execute(total_query)).scalar() or 0
        return list(rows), total
