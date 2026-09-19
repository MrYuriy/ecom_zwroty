from enum import StrEnum


class ReturnStatus(StrEnum):
    # OPEN while the operator is receiving items; CLOSED = finished and ready for the report export.
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CarrierType(StrEnum):
    PARCEL = "PARCEL"
    PALLET = "PALLET"


class GoodsCondition(StrEnum):
    DAMAGED = "DAMAGED"
    FULL_VALUE = "FULL_VALUE"
