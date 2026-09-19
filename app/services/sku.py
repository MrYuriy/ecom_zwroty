from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import ObjectAlreadyExistsException, ObjectNotFoundException
from app.database.postgres import get_session
from app.repositories.return_order import LineImageRepository
from app.repositories.sku import SkuRepository
from app.schemas.common import Page
from app.schemas.sku import SkuCreate, SkuOut, SkuUpdate
from app.services.image_naming import ImageNamer
from app.services.image_storage import ImageStorage


class SkuService:
    def __init__(self, session: AsyncSession) -> None:
        self.skus = SkuRepository(session)
        self.images = LineImageRepository(session)
        self.namer = ImageNamer(session, ImageStorage())

    async def _ensure_unique(self, trade_reference: str | None, ean: str | None, exclude_id: int | None = None) -> None:
        if trade_reference:
            existing = await self.skus.get_one(trade_reference=trade_reference)
            if existing and existing.id != exclude_id:
                raise ObjectAlreadyExistsException(trade_reference, "SKU")
        if ean:
            existing = await self.skus.get_one(ean=ean)
            if existing and existing.id != exclude_id:
                raise ObjectAlreadyExistsException(ean, "EAN")

    async def create_sku(self, data: SkuCreate) -> SkuOut:
        await self._ensure_unique(data.trade_reference, data.ean)
        sku = await self.skus.create_one(data.model_dump())
        return SkuOut.model_validate(sku)

    async def update_sku(self, sku_id: int, data: SkuUpdate) -> SkuOut:
        sku = await self.skus.get_one(id=sku_id)
        if not sku:
            raise ObjectNotFoundException(sku_id, "SKU")
        # Only ean may be cleared; a null on a required field is ignored.
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k == "ean"}
        await self._ensure_unique(changes.get("trade_reference"), changes.get("ean"), exclude_id=sku_id)
        new_reference = changes.get("trade_reference", sku.trade_reference) != sku.trade_reference
        sku = await self.skus.update_one(sku, changes)
        out = SkuOut.model_validate(sku)
        # Photo names carry the reference; every photo of this SKU moves to the new name wholesale.
        if new_reference:
            await self.namer.renumber_quietly(await self.images.keys_for_sku(sku_id))
        return out

    async def get_sku(self, sku_id: int) -> SkuOut:
        sku = await self.skus.get_one(id=sku_id)
        if not sku:
            raise ObjectNotFoundException(sku_id, "SKU")
        return SkuOut.model_validate(sku)

    async def get_by_ean(self, ean: str) -> SkuOut:
        sku = await self.skus.get_one(ean=ean.strip())
        if not sku:
            raise ObjectNotFoundException(ean, "SKU with EAN")
        return SkuOut.model_validate(sku)

    async def search(self, query: str | None, page: int, limit: int) -> Page[SkuOut]:
        skus, total = await self.skus.search(query, page=page, limit=limit)
        return Page(items=[SkuOut.model_validate(s) for s in skus], total=total, page=page, limit=limit)


def get_sku_service(session: AsyncSession = Depends(get_session)) -> SkuService:
    return SkuService(session)
