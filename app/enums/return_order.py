from enum import StrEnum


class CarrierType(StrEnum):
    PARCEL = "PARCEL"
    PALLET = "PALLET"


class GoodsCondition(StrEnum):
    DAMAGED = "DAMAGED"
    FULL_VALUE = "FULL_VALUE"
