from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.return_order import OrderLine, ReturnOrder
from app.models.sku import Sku, SkuEan
from app.repositories.base import BaseRepository


class SkuRepository(BaseRepository[Sku]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sku)

    async def reload(self, sku_id: int) -> Sku | None:
        # populate_existing: pick up the codes even when this SKU is already in the session.
        query = select(Sku).where(Sku.id == sku_id).execution_options(populate_existing=True)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_ean(self, ean: str) -> Sku | None:
        query = select(Sku).join(SkuEan, SkuEan.sku_id == Sku.id).where(SkuEan.ean == ean)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def eans_of_other_skus(self, eans: list[str], sku_id: int | None) -> list[str]:
        if not eans:
            return []
        query = select(SkuEan.ean).where(SkuEan.ean.in_(eans))
        if sku_id is not None:
            query = query.where(SkuEan.sku_id != sku_id)
        return sorted((await self.session.execute(query)).scalars().all())

    async def usage(self, sku_id: int) -> list[tuple[ReturnOrder, int]]:
        """Returns that have lines with this SKU, newest first, with the number of such lines."""
        query = (
            select(ReturnOrder, func.count(OrderLine.uuid))
            .join(OrderLine, OrderLine.return_order_uuid == ReturnOrder.uuid)
            .where(OrderLine.sku_id == sku_id)
            .group_by(ReturnOrder.uuid)
            .order_by(ReturnOrder.return_date.desc(), ReturnOrder.created_at.desc())
        )
        return [(order, lines) for order, lines in (await self.session.execute(query)).all()]

    async def search(self, query: str | None, page: int, limit: int) -> tuple[list[Sku], int]:
        condition = None
        if query:
            pattern = f"%{query}%"
            # Codes are matched from the start: a scanned or typed EAN, not any fragment of 600k codes.
            by_code = select(SkuEan.sku_id).where(SkuEan.ean.like(f"{query}%"))
            condition = or_(
                Sku.trade_reference.ilike(pattern),
                Sku.product_name.ilike(pattern),
                Sku.id.in_(by_code),
            )

        rows_query = select(Sku).order_by(Sku.trade_reference).offset((page - 1) * limit).limit(limit)
        total_query = select(func.count()).select_from(Sku)
        if condition is not None:
            rows_query = rows_query.where(condition)
            total_query = total_query.where(condition)

        rows = (await self.session.execute(rows_query)).scalars().all()
        total = (await self.session.execute(total_query)).scalar() or 0
        return list(rows), total
