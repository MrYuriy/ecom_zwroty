from datetime import datetime, timedelta

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.sku_import import SkuImportStatus
from app.models.sku import Sku, SkuEan
from app.models.sku_import import SkuImport
from app.repositories.base import BaseRepository

_BATCH = 5000


class SkuImportRepository(BaseRepository[SkuImport]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SkuImport)

    async def latest(self) -> SkuImport | None:
        query = select(SkuImport).order_by(SkuImport.created_at.desc()).limit(1)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def running(self, stale_after: timedelta) -> SkuImport | None:
        """An import still in progress; one stuck for longer than `stale_after` (e.g. a restart) doesn't count."""
        query = select(SkuImport).where(
            SkuImport.status.in_([SkuImportStatus.PENDING, SkuImportStatus.RUNNING]),
            SkuImport.updated_at > datetime.now() - stale_after,
        )
        return (await self.session.execute(query.limit(1))).scalar_one_or_none()


class SkuBulkRepository:
    """Set-based writes for the file import: hundreds of thousands of rows, one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sku_map(self) -> dict[str, tuple[int, str, bool]]:
        rows = await self.session.execute(select(Sku.trade_reference, Sku.id, Sku.product_name, Sku.is_parametrized))
        return {reference: (sku_id, name, flag) for reference, sku_id, name, flag in rows.all()}

    async def ean_map(self) -> dict[str, tuple[int, int]]:
        rows = await self.session.execute(select(SkuEan.ean, SkuEan.id, SkuEan.sku_id))
        return {ean: (ean_id, sku_id) for ean, ean_id, sku_id in rows.all()}

    async def insert_skus(self, rows: list[dict]) -> None:
        for start in range(0, len(rows), _BATCH):
            await self.session.execute(insert(Sku), rows[start : start + _BATCH])

    async def update_skus(self, rows: list[dict]) -> None:
        # ORM bulk UPDATE by primary key: each dict carries "id" plus the changed columns.
        for start in range(0, len(rows), _BATCH):
            await self.session.execute(update(Sku), rows[start : start + _BATCH])

    async def insert_eans(self, rows: list[dict]) -> None:
        for start in range(0, len(rows), _BATCH):
            await self.session.execute(insert(SkuEan), rows[start : start + _BATCH])

    async def update_eans(self, rows: list[dict]) -> None:
        for start in range(0, len(rows), _BATCH):
            await self.session.execute(update(SkuEan), rows[start : start + _BATCH])
