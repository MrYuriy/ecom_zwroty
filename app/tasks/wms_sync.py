import asyncio
import logging

from app.core import settings
from app.database.postgres import async_session
from app.services.google_sheets import GoogleSheetsClient
from app.services.wms_order import WmsOrderService

logger = logging.getLogger(__name__)


async def sync_once(sheets: GoogleSheetsClient) -> None:
    async with async_session() as session:
        await WmsOrderService(session, sheets).sync_from_sheet()


async def run_periodic_sync() -> None:
    """Import new WMS orders now and then every WMS_SYNC_INTERVAL_MINUTES, until cancelled."""
    sheets = GoogleSheetsClient()
    interval = settings.google.WMS_SYNC_INTERVAL_MINUTES * 60
    while True:
        try:
            await sync_once(sheets)
        except asyncio.CancelledError:
            raise
        except Exception:
            # A Google or network hiccup must not kill the loop; the next run retries.
            logger.exception("WMS sheet sync failed")
        await asyncio.sleep(interval)
