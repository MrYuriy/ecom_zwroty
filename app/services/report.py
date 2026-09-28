"""The returns report row, in the exact column layout of the report sheet."""

from app.enums.return_order import CarrierType, GoodsCondition
from app.models.return_order import OrderLine

NO_NUMBER = "brak"

REPORT_COLUMNS = [
    "DATA ZWROTU",
    "NUMER BO/WMS",
    "NUMER TEMPO",
    "REFERENCJA HANDLOWA",
    "Produkt sparametryzowany",
    "UWAGI",
    "ILOŚĆ",
    "NOŚNIK",
    "KLASYFIKACJA TOWARU",
    "OPIS USZKODZENIA",
]

CARRIER_LABELS = {CarrierType.PARCEL: "paczka", CarrierType.PALLET: "paleta"}
CONDITION_LABELS = {GoodsCondition.DAMAGED: "uszkodzony", GoodsCondition.FULL_VALUE: "pełnowartościowy"}


def report_rows(line: OrderLine) -> list[list[str | int]]:
    """One row for the intact pieces and one for the damaged ones; empty halves are left out.

    Needs line.return_order and line.sku loaded.
    """
    rows = []
    if line.quantity_intact:
        rows.append(_row(line, line.quantity_intact, GoodsCondition.FULL_VALUE))
    if line.quantity_damaged:
        rows.append(_row(line, line.quantity_damaged, GoodsCondition.DAMAGED))
    return rows


def _row(line: OrderLine, quantity: int, condition: GoodsCondition) -> list[str | int]:
    order = line.return_order
    return [
        order.return_date.isoformat(),
        order.bo_wms_number or NO_NUMBER,
        order.tempo_number or NO_NUMBER,
        line.sku.trade_reference,
        "tak" if line.sku.is_parametrized else "nie",
        line.remarks or "",
        quantity,
        CARRIER_LABELS[line.carrier_type],
        CONDITION_LABELS[condition],
        # The damage description belongs to the damaged pieces only.
        (line.damage_description or "") if condition is GoodsCondition.DAMAGED else "",
    ]
