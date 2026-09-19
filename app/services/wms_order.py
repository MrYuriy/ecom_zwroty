import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings
from app.core.exc import BadRequestException, ObjectNotFoundException
from app.database.postgres import get_session
from app.repositories.wms_order import WmsOrderRepository
from app.schemas.wms_order import WmsOrderOut, WmsSyncResult
from app.services.google_sheets import GoogleSheetsClient, get_sheets_client

logger = logging.getLogger(__name__)

_HEADER = "ORDER_ID"


def _cell(row: list[str], index: int) -> str | None:
    value = row[index].strip() if len(row) > index and row[index] is not None else ""
    return value or None


def parse_rows(values: list[list[str]]) -> dict[str, str | None]:
    """ORDER_ID (column A) → CUSTOMER_ID (column B); header and blank rows skipped, first occurrence wins."""
    pairs: dict[str, str | None] = {}
    for row in values:
        bo_wms_number = _cell(row, 0)
        if not bo_wms_number or bo_wms_number.upper() == _HEADER:
            continue
        pairs.setdefault(bo_wms_number, _cell(row, 1))
    return pairs


class WmsOrderService:
    def __init__(self, session: AsyncSession, sheets: GoogleSheetsClient) -> None:
        self.orders = WmsOrderRepository(session)
        self.sheets = sheets

    async def get(self, bo_wms_number: str) -> WmsOrderOut:
        order = await self.orders.get_one(bo_wms_number=bo_wms_number.strip())
        if not order:
            raise ObjectNotFoundException(bo_wms_number, "WMS order")
        return WmsOrderOut.model_validate(order)

    async def sync_from_sheet(self) -> WmsSyncResult:
        """Add orders that appeared in the sheet since the last run; existing ones are left as they are."""
        if not settings.google.WMS_SHEET_ID:
            raise BadRequestException("WMS_SHEET_ID is not configured")
        values = await self.sheets.read_columns(settings.google.WMS_SHEET_ID, settings.google.WMS_SHEET_GID)
        pairs = parse_rows(values)
        existing = await self.orders.existing_numbers()
        new_rows = [
            {"bo_wms_number": number, "tempo_number": tempo}
            for number, tempo in pairs.items()
            if number not in existing
        ]
        if new_rows:
            await self.orders.insert_many(new_rows)
        logger.info("WMS sheet sync: %d rows, %d new", len(pairs), len(new_rows))
        return WmsSyncResult(rows=len(pairs), added=len(new_rows))


def get_wms_order_service(
    session: AsyncSession = Depends(get_session),
    sheets: GoogleSheetsClient = Depends(get_sheets_client),
) -> WmsOrderService:
    return WmsOrderService(session, sheets)
