from pathlib import Path
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import ObjectNotFoundException
from app.database.postgres import get_session
from app.models.line_image import LineImage
from app.repositories.integration import IntegrationRepository
from app.schemas.integration import AckResult, ImageItem, ImagesOut, ReportLineItem, ReportLinesOut
from app.services.image_storage import ImageStorage
from app.services.report import NO_NUMBER, REPORT_COLUMNS, report_row


class IntegrationService:
    """Hands report rows and photos to an external script, each exactly once (fetch → write → acknowledge)."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = IntegrationRepository(session)
        self.storage = ImageStorage()

    async def report_lines(self, limit: int) -> ReportLinesOut:
        lines, total = await self.repo.pending_lines(limit)
        return ReportLinesOut(
            columns=REPORT_COLUMNS,
            items=[ReportLineItem(line_uuid=line.uuid, row=report_row(line)) for line in lines],
            remaining=total - len(lines),
        )

    async def acknowledge_lines(self, line_uuids: list[UUID]) -> AckResult:
        return AckResult(acknowledged=await self.repo.mark_lines_exported(line_uuids))

    async def images(self, limit: int, base_url: str) -> ImagesOut:
        images, total = await self.repo.pending_images(limit)
        return ImagesOut(items=[_image_item(image, base_url) for image in images], remaining=total - len(images))

    async def acknowledge_images(self, image_uuids: list[UUID]) -> AckResult:
        return AckResult(acknowledged=await self.repo.mark_images_downloaded(image_uuids))

    async def image_file(self, image_uuid: UUID) -> tuple[Path, str, str]:
        image = await self.repo.get_image(image_uuid)
        path = self.storage.path_of(image.file_name) if image else None
        if not image or not path.is_file():
            raise ObjectNotFoundException(image_uuid, "Image")
        return path, image.content_type, image.file_name


def _image_item(image: LineImage, base_url: str) -> ImageItem:
    line = image.line
    return ImageItem(
        image_uuid=image.uuid,
        file_name=image.file_name,
        content_type=image.content_type,
        size_bytes=image.size_bytes,
        url=f"{base_url}/api/integration/images/{image.uuid}",
        line_uuid=line.uuid,
        return_date=line.return_order.return_date,
        bo_wms_number=line.return_order.bo_wms_number or NO_NUMBER,
        trade_reference=line.sku.trade_reference,
    )


def get_integration_service(session: AsyncSession = Depends(get_session)) -> IntegrationService:
    return IntegrationService(session)
