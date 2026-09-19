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


def report_row(line: OrderLine) -> list[str | int]:
    """Needs line.return_order and line.sku loaded."""
    order = line.return_order
    return [
        order.return_date.isoformat(),
        order.bo_wms_number or NO_NUMBER,
        order.tempo_number or NO_NUMBER,
        line.sku.trade_reference,
        "tak" if line.sku.is_parametrized else "nie",
        line.remarks or "",
        line.quantity,
        CARRIER_LABELS[line.carrier_type],
        CONDITION_LABELS[line.goods_condition],
        line.damage_description or "",
    ]
