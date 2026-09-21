from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import ObjectAlreadyExistsException, ObjectNotFoundException
from app.database.postgres import get_session
from app.models.sku import Sku, SkuEan
from app.repositories.return_order import LineImageRepository
from app.repositories.sku import SkuRepository
from app.schemas.common import Page
from app.schemas.sku import SkuCreate, SkuOut, SkuUpdate
from app.services.image_naming import ImageNamer
from app.services.image_storage import ImageStorage


class SkuService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.skus = SkuRepository(session)
        self.images = LineImageRepository(session)
        self.namer = ImageNamer(session, ImageStorage())

    async def _ensure_unique(self, trade_reference: str | None, eans: list[str] | None, sku_id: int | None) -> None:
        if trade_reference:
            existing = await self.skus.get_one(trade_reference=trade_reference)
            if existing and existing.id != sku_id:
                raise ObjectAlreadyExistsException(trade_reference, "SKU")
        # By hand a code is never moved silently between products (the file import does that on purpose).
        taken = await self.skus.eans_of_other_skus(eans or [], sku_id)
        if taken:
            raise ObjectAlreadyExistsException(", ".join(taken), "EAN of another SKU")

    async def _out(self, sku_id: int) -> SkuOut:
        return SkuOut.model_validate(await self.skus.reload(sku_id))

    async def create_sku(self, data: SkuCreate) -> SkuOut:
        await self._ensure_unique(data.trade_reference, data.eans, None)
        sku = Sku(
            trade_reference=data.trade_reference,
            product_name=data.product_name,
            is_parametrized=data.is_parametrized,
            eans=[SkuEan(ean=code) for code in data.eans],
        )
        self.session.add(sku)
        await self.session.commit()
        return await self._out(sku.id)

    async def update_sku(self, sku_id: int, data: SkuUpdate) -> SkuOut:
        sku = await self.skus.reload(sku_id)
        if not sku:
            raise ObjectNotFoundException(sku_id, "SKU")
        # A null on a required field is ignored; eans=None keeps the codes.
        changes = {k: v for k, v in data.model_dump(exclude_unset=True, exclude={"eans"}).items() if v is not None}
        await self._ensure_unique(changes.get("trade_reference"), data.eans, sku_id)
        new_reference = changes.get("trade_reference", sku.trade_reference) != sku.trade_reference

        for field, value in changes.items():
            setattr(sku, field, value)
        if data.eans is not None:
            kept = {code.ean: code for code in sku.eans}
            sku.eans = [kept.get(code) or SkuEan(ean=code) for code in data.eans]
        await self.session.commit()

        out = await self._out(sku_id)
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
        sku = await self.skus.get_by_ean(ean.strip())
        if not sku:
            raise ObjectNotFoundException(ean, "SKU with EAN")
        return SkuOut.model_validate(sku)

    async def search(self, query: str | None, page: int, limit: int) -> Page[SkuOut]:
        skus, total = await self.skus.search(query.strip() if query else None, page=page, limit=limit)
        return Page(items=[SkuOut.model_validate(s) for s in skus], total=total, page=page, limit=limit)


def get_sku_service(session: AsyncSession = Depends(get_session)) -> SkuService:
    return SkuService(session)
