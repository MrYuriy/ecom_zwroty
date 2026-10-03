"""Zebra labels for a closed return, sent to the cups server that an ESP printer polls.

One record per kind of goods; cups splits it into 10x10 cm sheets (1/3, 2/3, 3/3) and builds the ZPL.
Printing must never block finishing a return, so failures are logged and swallowed.
"""

import logging

import httpx

from app.core import settings
from app.models.return_order import ReturnOrder

logger = logging.getLogger(__name__)

NO_NUMBER = "brak"


def _rows(order: ReturnOrder, damaged: bool) -> list[dict]:
    """Reference and quantity per line, keeping the order the items were received in."""
    rows = []
    for line in order.lines:
        quantity = line.quantity_damaged if damaged else line.quantity_intact
        if quantity:
            rows.append({"reference": line.sku.trade_reference, "quantity": quantity})
    return rows


def build_payload(order: ReturnOrder) -> list[dict]:
    """A record per kind of goods; a kind with nothing in it is not printed at all."""
    header = {
        "data": order.return_date.strftime("%d.%m.%Y"),
        "oh_number": order.bo_wms_number or NO_NUMBER,
    }
    records = []
    for kind, damaged in (("intact", False), ("damaged", True)):
        rows = _rows(order, damaged)
        if rows:
            records.append({**header, "kind": kind, "lines_info": rows})
    return records


async def print_return_labels(order: ReturnOrder) -> None:
    url = settings.printing.LABELS_URL
    if not url:
        return
    records = build_payload(order)
    if not records:
        return
    try:
        async with httpx.AsyncClient(timeout=settings.printing.TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=records)
        if response.is_error:
            # The body says which field the print server rejected; without it a 400 is a guess.
            raise RuntimeError(f"{response.status_code}: {response.text[:300]}")
        logger.info("Labels for return %s sent to the printer (%s records)", order.uuid, len(records))
    except Exception as error:  # noqa: BLE001 — a dead printer must not stop the warehouse
        logger.warning("Labels for return %s were not sent: %s", order.uuid, error)
