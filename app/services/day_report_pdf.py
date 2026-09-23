"""The daily paper form "ZWROTY OD KLIENTÓW" (PL-FORM-CL-LM-038) as a PDF.

The blank form is a scan; the generator only draws the received items onto it, so the
printout matches the form the warehouse signs. Coordinates are in the scan's own grid.
"""

import io
from datetime import date
from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.enums.return_order import CarrierType, GoodsCondition
from app.models.return_order import OrderLine
from app.repositories.return_order import ReturnOrderRepository
from app.repositories.work_log import WorkLogRepository

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "pdf"
_FORM_IMAGE = _ASSETS / "zwroty_od_klientow.jpg"
_FONT_FILE = _ASSETS / "FreeSans.ttf"
_FONT = "FreeSans"

# The scan fills the whole page; these keep its printed grid where the eye expects it.
_IMAGE_BOX = (-10, 0, 622, 850)
_ROW_X = (55, 125, 285, 380, 430, 485)
_FIRST_ROW_Y = 615
_ROW_HEIGHT = 26
_ROWS_PER_PAGE = 17
_FONT_SIZE = 12
# Width of the "Opis" cell on the scan; a longer name is cut so it can't run into "Ilość".
_NAME_WIDTH = 150

_DAY_XY = (365, 690)
# The box for the verification time, drawn where the scan's "strona ……" line used to be.
_TIME_BOX = (48, 76, 551, 106)  # as wide as the table above it
_TIME_BOX_DIVIDER = 325
_PARCELS_XY = (92, 147)
_PALLETS_XY = (270, 147)

_CONDITION = {GoodsCondition.DAMAGED: "U", GoodsCondition.FULL_VALUE: "P"}
_CARRIER = {CarrierType.PARCEL: "paczka", CarrierType.PALLET: "paleta"}
_NO_NUMBER = "brak"


@lru_cache(maxsize=1)
def _register_font() -> None:
    pdfmetrics.registerFont(TTFont(_FONT, str(_FONT_FILE)))


def _fit(text: str, width: float) -> str:
    """Trim a name to what its cell holds, adding an ellipsis when something was cut."""
    if pdfmetrics.stringWidth(text, _FONT, _FONT_SIZE) <= width:
        return text
    while text and pdfmetrics.stringWidth(text + "…", _FONT, _FONT_SIZE) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _row(line: OrderLine, first_of_return: bool) -> list[str]:
    """One printed line: reference, name, quantity, U/P, carrier, order number."""
    number = line.return_order.bo_wms_number or _NO_NUMBER
    return [
        line.sku.trade_reference,
        _fit(line.sku.product_name, _NAME_WIDTH),
        str(line.quantity),
        _CONDITION[line.goods_condition],
        _CARRIER[line.carrier_type],
        # The number belongs to the whole return, so it is written once, on its first item.
        number if first_of_return else "",
    ]


def _totals(lines: list[OrderLine]) -> tuple[int, int]:
    parcels = sum(line.quantity for line in lines if line.carrier_type == CarrierType.PARCEL)
    pallets = sum(line.quantity for line in lines if line.carrier_type == CarrierType.PALLET)
    return parcels, pallets


class DayReportPdfService:
    def __init__(self, session: AsyncSession) -> None:
        self.returns = ReturnOrderRepository(session)
        self.work_logs = WorkLogRepository(session)

    async def build(self, day: date) -> io.BytesIO:
        lines = await self.returns.lines_for_day(day)
        return _render(day, lines, await self.work_logs.minutes_for_day(day))


def _draw_time_box(sheet: canvas.Canvas, minutes: int | None) -> None:
    """The framed "CZAS WERYFIKACJI ZWROTÓW | MIN:" cells; the number only when the day has a work log."""
    left, bottom, right, top = _TIME_BOX
    sheet.rect(left, bottom, right - left, top - bottom)
    sheet.line(_TIME_BOX_DIVIDER, bottom, _TIME_BOX_DIVIDER, top)
    text_y = bottom + 10
    sheet.setFont(_FONT, _FONT_SIZE)
    sheet.drawString(left + 6, text_y, "CZAS WERYFIKACJI ZWROTÓW")
    sheet.drawString(_TIME_BOX_DIVIDER + 6, text_y, f"MIN: {minutes}" if minutes is not None else "MIN:")


def _render(day: date, lines: list[OrderLine], minutes: int | None = None) -> io.BytesIO:
    _register_font()
    buffer = io.BytesIO()
    sheet = canvas.Canvas(buffer)

    def new_page() -> None:
        sheet.drawImage(str(_FORM_IMAGE), *_IMAGE_BOX)
        sheet.setFont(_FONT, _FONT_SIZE)
        sheet.drawString(*_DAY_XY, day.isoformat())

    new_page()
    y = _FIRST_ROW_Y
    printed = 0
    seen_returns: set = set()

    for line in lines:
        if printed == _ROWS_PER_PAGE:
            sheet.showPage()
            new_page()
            y = _FIRST_ROW_Y
            printed = 0
        first_of_return = line.return_order_uuid not in seen_returns
        seen_returns.add(line.return_order_uuid)
        for x, value in zip(_ROW_X, _row(line, first_of_return), strict=True):
            sheet.drawString(x, y, value)
        printed += 1
        y -= _ROW_HEIGHT

    # "Liczba przyjętych" is a summary of the whole day, so it goes on the last page only.
    parcels, pallets = _totals(lines)
    sheet.setFont(_FONT, _FONT_SIZE)
    sheet.drawString(*_PARCELS_XY, str(parcels))
    sheet.drawString(*_PALLETS_XY, str(pallets))
    _draw_time_box(sheet, minutes)

    sheet.showPage()
    sheet.save()
    buffer.seek(0)
    return buffer


def get_day_report_pdf_service(session: AsyncSession = Depends(get_session)) -> DayReportPdfService:
    return DayReportPdfService(session)
