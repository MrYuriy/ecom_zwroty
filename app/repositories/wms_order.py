from sqlalchemy import insert, select
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

