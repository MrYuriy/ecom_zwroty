from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.return_order import CarrierType, GoodsCondition, ReturnStatus
from app.schemas.sku import SkuOut

_NO_NUMBER = "brak"


def _normalize_number(value: str | None) -> str | None:
    # Blank and "brak" both mean "the order has no number" and are stored as NULL.
    if value is None:
        return None
    value = value.strip()
    if not value or value.lower() == _NO_NUMBER:
        return None
    return value


class OrderLineCreate(BaseModel):
    sku_id: int
    quantity: int = Field(ge=1)
    carrier_type: CarrierType
    goods_condition: GoodsCondition
    damage_description: str | None = None
    remarks: str | None = None


class OrderLineUpdate(BaseModel):
    sku_id: int | None = None
    quantity: int | None = Field(None, ge=1)
    carrier_type: CarrierType | None = None
    goods_condition: GoodsCondition | None = None
    damage_description: str | None = None
    remarks: str | None = None


class LineImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime
    downloaded_at: datetime | None


class OrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    sku: SkuOut
    images: list[LineImageOut]
    quantity: int
    carrier_type: CarrierType
    goods_condition: GoodsCondition
    damage_description: str | None
    remarks: str | None
    created_at: datetime
    exported_at: datetime | None


class ReturnOrderCreate(BaseModel):
    bo_wms_number: str | None = Field(None, max_length=64)
    tempo_number: str | None = Field(None, max_length=64)
    return_date: date | None = None

    @field_validator("bo_wms_number", "tempo_number")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return _normalize_number(value)


class ReturnOrderUpdate(ReturnOrderCreate):
    pass


class ReturnOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    bo_wms_number: str | None
    tempo_number: str | None
    return_date: date
    operator_id: int
    status: ReturnStatus
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[OrderLineOut]
