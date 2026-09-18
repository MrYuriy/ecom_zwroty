from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sku import Sku
from app.repositories.base import BaseRepository


class SkuRepository(BaseRepository[Sku]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sku)

    async def search(self, query: str | None, page: int, limit: int) -> tuple[list[Sku], int]:
        condition = None
        if query:
            pattern = f"%{query}%"
            condition = or_(Sku.trade_reference.ilike(pattern), Sku.ean.ilike(pattern), Sku.product_name.ilike(pattern))

        rows_query = select(Sku).order_by(Sku.trade_reference).offset((page - 1) * limit).limit(limit)
        total_query = select(func.count()).select_from(Sku)
        if condition is not None:
            rows_query = rows_query.where(condition)
            total_query = total_query.where(condition)

        rows = (await self.session.execute(rows_query)).scalars().all()
        total = (await self.session.execute(total_query)).scalar() or 0
        return list(rows), total
