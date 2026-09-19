import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.line_image import LineImage
from app.repositories.return_order import LineImageRepository
from app.services.image_storage import ImageStorage, image_file_name, number_in_name

logger = logging.getLogger(__name__)

ImageKey = tuple[str | None, str]  # (BO/WMS number, SKU trade reference)


def _sort_key(image: LineImage) -> tuple:
    # Oldest first; within one upload the temporary names keep the upload order,
    # and already numbered photos keep their relative order.
    number = number_in_name(image.file_name)
    return (image.created_at, number if number is not None else float("inf"), image.file_name)


class ImageNamer:
    """Keeps photo files named {BO/WMS or brak}_{reference}_{N}, N = 1..k per (BO/WMS, reference) pair."""

    def __init__(self, session: AsyncSession, storage: ImageStorage) -> None:
        self.session = session
        self.images = LineImageRepository(session)
        self.storage = storage

    async def renumber(self, keys: set[ImageKey]) -> int:
        """Returns how many files were renamed."""
        plan: list[tuple[LineImage, str, str]] = []  # (image, old name, new name)
        for bo_wms_number, trade_reference in keys:
            images = sorted(await self.images.for_key(bo_wms_number, trade_reference), key=_sort_key)
            for number, image in enumerate(images, start=1):
                new_name = image_file_name(bo_wms_number, trade_reference, number, image.content_type)
                if image.file_name != new_name:
                    plan.append((image, image.file_name, new_name))
        if not plan:
            return 0

        await self.storage.rename([(old, new) for _, old, new in plan])
        try:
            # Two steps, so a name freed and taken in the same batch never trips the unique constraint.
            for image, _, _ in plan:
                image.file_name = f"renaming-{image.uuid.hex}"
            await self.session.flush()
            for image, _, new in plan:
                image.file_name = new
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            await self.storage.rename([(new, old) for _, old, new in plan])
            raise
        return len(plan)

    async def renumber_quietly(self, keys: set[ImageKey]) -> None:
        """Renaming is cosmetic: a failure is logged, never allowed to undo the change that triggered it."""
        try:
            await self.renumber(keys)
        except Exception:
            logger.exception("Renaming line photos failed for %s", sorted(keys, key=str))
