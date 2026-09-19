from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums.return_order import ReturnStatus
from app.models.line_image import LineImage
from app.models.return_order import OrderLine, ReturnOrder


class IntegrationRepository:
    """What the export script has not picked up yet: lines and photos of CLOSED returns."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _pending_lines():
        return (
            select(OrderLine)
            .join(ReturnOrder, ReturnOrder.uuid == OrderLine.return_order_uuid)
            .where(ReturnOrder.status == ReturnStatus.CLOSED, OrderLine.exported_at.is_(None))
        )

    async def pending_lines(self, limit: int) -> tuple[list[OrderLine], int]:
        query = (
            self._pending_lines()
            .options(selectinload(OrderLine.sku), selectinload(OrderLine.return_order))
            .order_by(ReturnOrder.return_date, ReturnOrder.created_at, OrderLine.created_at, OrderLine.uuid)
            .limit(limit)
        )
        total_query = select(func.count()).select_from(self._pending_lines().subquery())
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows), (await self.session.execute(total_query)).scalar() or 0

    @staticmethod
    def _pending_images():
        return (
            select(LineImage)
            .join(OrderLine, OrderLine.uuid == LineImage.order_line_uuid)
            .join(ReturnOrder, ReturnOrder.uuid == OrderLine.return_order_uuid)
            .where(ReturnOrder.status == ReturnStatus.CLOSED, LineImage.downloaded_at.is_(None))
        )

    async def pending_images(self, limit: int) -> tuple[list[LineImage], int]:
        query = (
            self._pending_images()
            .options(
                selectinload(LineImage.line).options(selectinload(OrderLine.sku), selectinload(OrderLine.return_order))
            )
            .order_by(ReturnOrder.return_date, ReturnOrder.created_at, LineImage.file_name)
            .limit(limit)
        )
        total_query = select(func.count()).select_from(self._pending_images().subquery())
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows), (await self.session.execute(total_query)).scalar() or 0

    async def get_image(self, image_uuid: UUID) -> LineImage | None:
        return await self.session.get(LineImage, image_uuid)

    async def mark_lines_exported(self, line_uuids: list[UUID]) -> int:
        # Only lines not acknowledged before, so a repeated ack is harmless and reports 0.
        result = await self.session.execute(
            update(OrderLine)
            .where(OrderLine.uuid.in_(line_uuids), OrderLine.exported_at.is_(None))
            .values(exported_at=func.now())
        )
        await self.session.commit()
        return result.rowcount or 0

    async def mark_images_downloaded(self, image_uuids: list[UUID]) -> int:
        result = await self.session.execute(
            update(LineImage)
            .where(LineImage.uuid.in_(image_uuids), LineImage.downloaded_at.is_(None))
            .values(downloaded_at=func.now())
        )
        await self.session.commit()
        return result.rowcount or 0
