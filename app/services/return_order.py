from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings
from app.core.exc import BadRequestException, ObjectNotFoundException
from app.database.postgres import get_session
from app.models.line_image import LineImage
from app.models.return_order import OrderLine, ReturnOrder
from app.repositories.return_order import LineImageRepository, OrderLineRepository, ReturnOrderRepository
from app.repositories.sku import SkuRepository
from app.schemas.common import Page
from app.schemas.return_order import (
    OrderLineCreate,
    OrderLineUpdate,
    ReturnOrderCreate,
    ReturnOrderOut,
    ReturnOrderUpdate,
)
from app.services.image_storage import ImageStorage, detect_image_type

_CLEARABLE_LINE_FIELDS = {"damage_description", "remarks"}


class ReturnOrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orders = ReturnOrderRepository(session)
        self.lines = OrderLineRepository(session)
        self.images = LineImageRepository(session)
        self.skus = SkuRepository(session)
        self.storage = ImageStorage()

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
        order = await self._get_order(order_uuid)
        file_names = await self.images.file_names_for_order(order_uuid)
        await self.orders.delete_one(order)
        # Files go only after the rows are gone, so a failed delete never leaves rows pointing at nothing.
        await self.storage.delete(file_names)

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
        line = await self._get_line(order_uuid, line_uuid)
        file_names = await self.images.file_names_for_line(line_uuid)
        await self.lines.delete_one(line)
        await self.storage.delete(file_names)
        return await self._reload(order_uuid)

    # ---------- line images ----------

    async def _read_image(self, upload: UploadFile) -> tuple[bytes, str]:
        max_bytes = settings.storage.MAX_IMAGE_MB * 1024 * 1024
        data = await upload.read(max_bytes + 1)
        name = upload.filename or "plik"
        if len(data) > max_bytes:
            raise BadRequestException(f"{name}: file is larger than {settings.storage.MAX_IMAGE_MB} MB")
        content_type = detect_image_type(data[:16])
        if content_type is None:
            raise BadRequestException(f"{name}: only JPEG, PNG and WebP images are accepted")
        return data, content_type

    async def add_images(self, order_uuid: UUID, line_uuid: UUID, uploads: list[UploadFile]) -> ReturnOrderOut:
        await self._get_line(order_uuid, line_uuid)
        if not uploads:
            raise BadRequestException("No files were sent")
        existing = await self.images.count_for_line(line_uuid)
        if existing + len(uploads) > settings.storage.MAX_IMAGES_PER_LINE:
            raise BadRequestException(f"A line can have at most {settings.storage.MAX_IMAGES_PER_LINE} images")

        # Validate every file before writing any, so one bad file doesn't leave half an upload behind.
        images = [await self._read_image(upload) for upload in uploads]
        saved: list[str] = []
        try:
            for data, content_type in images:
                file_name = await self.storage.save(data, content_type)
                saved.append(file_name)
                self.session.add(
                    LineImage(
                        order_line_uuid=line_uuid,
                        file_name=file_name,
                        content_type=content_type,
                        size_bytes=len(data),
                    )
                )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            await self.storage.delete(saved)
            raise
        return await self._reload(order_uuid)

    async def delete_image(self, order_uuid: UUID, line_uuid: UUID, image_uuid: UUID) -> ReturnOrderOut:
        await self._get_line(order_uuid, line_uuid)
        image = await self.images.get_one(uuid=image_uuid, order_line_uuid=line_uuid)
        if not image:
            raise ObjectNotFoundException(image_uuid, "Image")
        file_name = image.file_name
        await self.images.delete_one(image)
        await self.storage.delete([file_name])
        return await self._reload(order_uuid)

    async def get_image_file(self, image_uuid: UUID) -> tuple[Path, str]:
        image = await self.images.get_one(uuid=image_uuid)
        path = self.storage.path_of(image.file_name) if image else None
        if not image or not path.is_file():
            raise ObjectNotFoundException(image_uuid, "Image")
        return path, image.content_type


def get_return_order_service(session: AsyncSession = Depends(get_session)) -> ReturnOrderService:
    return ReturnOrderService(session)
